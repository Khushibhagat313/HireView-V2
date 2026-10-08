import argparse
import hashlib
import json
import time
from pathlib import Path

from groq import RateLimitError

from eval.metrics import (
    ceiling_coverage_at_k,
    empty_rate,
    mean_defined,
    ndcg_at_k,
    percentile,
    recall_at_k,
    reciprocal_rank,
    skill_coverage_at_k,
)
from src.agents import jd_parser
from src.agents.jd_parser import parse_jd
from src.config import EVAL_TARGETS
from src.ingestion.normalizer import normalize_skills
from src.retrieval.pipeline import search_and_score
from src.schemas.job import JDRequirements

EVAL_DIR = Path(__file__).parent
QUERIES_PATH = EVAL_DIR / "queries.jsonl"
RESUMES_PATH = EVAL_DIR / "data" / "resumes.json"
MAP_PATH = EVAL_DIR / "data" / "cand_id_map.json"
PARSED_PATH = EVAL_DIR / "data" / "parsed_jds.json"

QUALITY_METRICS = ["recall_at_20", "mrr", "ndcg_at_10", "skill_coverage_at_10", "coverage_ceiling_at_10"]


def load_queries() -> list[dict]:
    lines = QUERIES_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def jd_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def freeze_parses(queries: list[dict], reparse: bool) -> dict:
    parsed = {}
    if PARSED_PATH.exists() and not reparse:
        parsed = json.loads(PARSED_PATH.read_text(encoding="utf-8"))

    for query in queries:
        key = jd_hash(query["jd_text"])
        if key in parsed:
            continue
        for attempt in range(5):
            start = time.perf_counter()
            try:
                jd = parse_jd(query["jd_text"])
                break
            except RateLimitError:
                print("rate limited, waiting 30s")
                time.sleep(30)
        else:
            raise SystemExit("still rate limited; run again later (progress is saved)")
        parse_s = time.perf_counter() - start
        parsed[key] = {"query_id": query["query_id"], "jd": jd.model_dump(), "parse_s": parse_s}
        PARSED_PATH.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        print(f"parsed {query['query_id']} in {parse_s:.1f}s")
    return parsed


def prime_cache(parsed: dict) -> None:
    for key, entry in parsed.items():
        jd_parser._jd_cache[key] = JDRequirements(**entry["jd"])


def run_query(query: dict, company_id: str, reverse: dict, pool_skills: list[set[str]], threshold: float | None) -> dict:
    start = time.perf_counter()
    results = search_and_score(company_id, query["jd_text"], threshold=threshold)
    search_s = time.perf_counter() - start

    ranked = [reverse[r["resume_id"]] for r in results]
    grades = query["ground_truth"]
    required = normalize_skills(query["canonical_required_skills"])
    return {
        "query_id": query["query_id"],
        "difficulty": query["difficulty"],
        "results": len(results),
        "recall_at_20": recall_at_k(ranked, grades, 20),
        "mrr": reciprocal_rank(ranked, grades, min_grade=2),
        "ndcg_at_10": ndcg_at_k(ranked, grades, 10),
        "skill_coverage_at_10": skill_coverage_at_k(results, required, 10),
        "coverage_ceiling_at_10": ceiling_coverage_at_k(pool_skills, required, 10),
        "search_s": search_s,
    }


def summarize(rows: list[dict]) -> dict:
    summary = {name: mean_defined([row[name] for row in rows]) for name in QUALITY_METRICS}
    coverage, ceiling = summary["skill_coverage_at_10"], summary["coverage_ceiling_at_10"]
    summary["coverage_of_ceiling"] = coverage / ceiling if coverage is not None and ceiling else None
    summary["empty_rate"] = empty_rate([row["results"] for row in rows])
    summary["p95_search_s"] = percentile([row["search_s"] for row in rows], 95)
    return summary


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def print_table(rows: list[dict]) -> None:
    groups = {"all": rows}
    for difficulty in ("easy", "medium", "hard"):
        groups[difficulty] = [r for r in rows if r["difficulty"] == difficulty]

    print(f"{'group':<8}{'n':>4}{'recall@20':>11}{'mrr':>8}{'ndcg@10':>9}{'cov@10':>8}{'of ceil':>9}{'empty':>8}{'p95 s':>8}")
    for name, group in groups.items():
        if not group:
            continue
        s = summarize(group)
        print(
            f"{name:<8}{len(group):>4}{fmt(s['recall_at_20']):>11}{fmt(s['mrr']):>8}{fmt(s['ndcg_at_10']):>9}"
            f"{fmt(s['skill_coverage_at_10']):>8}{fmt(s['coverage_of_ceiling']):>9}{fmt(s['empty_rate']):>8}{s['p95_search_s']:>8.2f}"
        )


def print_targets(summary: dict) -> None:
    checks = [
        ("recall_at_20", summary["recall_at_20"], lambda v, t: v >= t),
        ("mrr", summary["mrr"], lambda v, t: v >= t),
        ("ndcg_at_10", summary["ndcg_at_10"], lambda v, t: v >= t),
        ("skill_coverage_at_10", summary["skill_coverage_at_10"], lambda v, t: v >= t),
        ("empty_rate", summary["empty_rate"], lambda v, t: v <= t),
        ("p95_latency_s", summary["p95_search_s"], lambda v, t: v < t),
    ]
    print()
    for name, value, passes in checks:
        target = EVAL_TARGETS[name]
        verdict = "n/a" if value is None else ("PASS" if passes(value, target) else "FAIL")
        print(f"{name:<22}{fmt(value):>8}  target {target}  {verdict}")
    print(
        f"\nskill coverage ceiling on this corpus: {fmt(summary['coverage_ceiling_at_10'])}"
        f" (system reaches {fmt(summary['coverage_of_ceiling'])} of it)"
    )


def print_lowest(rows: list[dict], count: int = 5) -> None:
    worst = sorted(rows, key=lambda r: r["ndcg_at_10"] if r["ndcg_at_10"] is not None else 1.0)[:count]
    print(f"\nlowest {count} by ndcg@10:")
    for row in worst:
        print(f"  {row['query_id']}: ndcg@10={fmt(row['ndcg_at_10'])}, mrr={fmt(row['mrr'])}, {row['results']} results")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reparse", action="store_true", help="re-run the JD parser instead of using the frozen parses")
    parser.add_argument("--threshold", type=float, default=None, help="override the display threshold (0 keeps every ranked result)")
    args = parser.parse_args()

    queries = load_queries()
    saved = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    company_id = saved["company_id"]
    reverse = {resume_id: cand_id for cand_id, resume_id in saved["resumes"].items()}
    pool_skills = [normalize_skills(r["skills"]) for r in json.loads(RESUMES_PATH.read_text(encoding="utf-8"))]

    parsed = freeze_parses(queries, args.reparse)
    prime_cache(parsed)

    rows = []
    for i, query in enumerate(queries, start=1):
        row = run_query(query, company_id, reverse, pool_skills, args.threshold)
        rows.append(row)
        print(f"[{i}/{len(queries)}] {row['query_id']}: {row['results']} results, ndcg@10={fmt(row['ndcg_at_10'])}, mrr={fmt(row['mrr'])}, {row['search_s']:.1f}s")

    print()
    print_table(rows)
    print_targets(summarize(rows))
    print_lowest(rows)


if __name__ == "__main__":
    main()
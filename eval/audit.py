import argparse
import json
from pathlib import Path

import src.retrieval.pipeline as pipeline
import src.scoring.eligibility as eligibility
from eval import memo
from eval.ablation import CONTEXT, ROWS, patched
from src.agents import jd_parser
from src.config import FIELD_MATCH_THRESHOLD
from src.db.store import get_resumes, get_work_experiences_many
from src.embedding.embedder import embed_documents, embed_query
from src.embedding.reranker import rerank
from src.retrieval.pipeline import search_and_score
from src.retrieval.query_builder import build_queries
from src.retrieval.searcher import search_candidates
from src.schemas.job import JDRequirements

DATA = Path("eval/data")
FACET_ABBR = {
    "skills": "S",
    "projects": "P",
    "experience": "E",
    "achievements_publications": "A",
    "education_certifications": "C",
}


def load():
    saved = json.loads((DATA / "cand_id_map.json").read_text(encoding="utf-8"))
    parsed = json.loads((DATA / "parsed_jds.json").read_text(encoding="utf-8"))
    for key, entry in parsed.items():
        jd_parser._jd_cache[key] = JDRequirements(**entry["jd"])
    resumes = {r["candidate_id"]: r for r in json.loads((DATA / "resumes.json").read_text(encoding="utf-8"))}
    lines = Path("eval/queries.jsonl").read_text(encoding="utf-8").splitlines()
    queries = {q["query_id"]: q for q in (json.loads(line) for line in lines if line.strip())}
    return saved, resumes, queries


def gate_detail(resume, jd, work):
    if not jd.min_years_experience:
        return "no minimum years parsed, so no experience gate"
    target = embed_query(jd.job_title)
    titles = []
    for w in work:
        sim = sum(x * y for x, y in zip(target, embed_documents([w.title])[0]))
        mark = "+" if sim >= FIELD_MATCH_THRESHOLD else "-"
        titles.append(f"{w.title} {w.duration_years}y sim {sim:.2f}{mark}")
    counted = eligibility.compute_field_specific_experience(jd.job_title, work)
    return f"min {jd.min_years_experience} | counted years {counted:.1f} | total {resume.years_experience:.1f} | " + "; ".join(titles)


def audit(qid, saved, resumes, queries):
    q = queries[qid]
    company_id = saved["company_id"]
    rid_of = saved["resumes"]
    cand_of = {rid: cand for cand, rid in rid_of.items()}
    category = {cand: r["category"] for cand, r in resumes.items()}
    truth = q["ground_truth"]
    jd = jd_parser.parse_jd(q["jd_text"])
    keep = pipeline.RERANK_KEEP_TOP_N

    retrieved = {str(r) for r in search_candidates(company_id, build_queries(jd))}
    reranked = rerank(company_id, jd.hyde_text, retrieved)
    rank_of = {str(rid): n for n, (rid, _) in enumerate(reranked, start=1)}
    kept = [str(rid) for rid, _ in reranked[:keep]]
    resume_rows = get_resumes(company_id, kept)
    work_rows = get_work_experiences_many(company_id, kept)
    passed = {rid: eligibility.check_eligibility(resume_rows[rid], jd, work_rows[rid]) for rid in kept}

    results = search_and_score(company_id, q["jd_text"])
    place = {r["resume_id"]: n for n, r in enumerate(results, start=1)}
    relevant = [c for c, g in truth.items() if g >= 1]
    hard_negatives = [c for c, g in truth.items() if g == 0]

    print(f"== {qid} | {q['difficulty']} | {q['category']}")
    print(
        f"   parsed title: {jd.job_title} | min years: {jd.min_years_experience} (author {q['min_years_experience']})"
        f" | grad years: {jd.eligible_graduation_years} (author {q['eligible_graduation_years']})"
        f" | required skills parsed: {len(jd.required_skills)}"
    )
    got = sum(rid_of[c] in place for c in relevant)
    print(f"   retrieved {len(retrieved)} | kept {len(kept)} | passed gate {sum(passed.values())} | returned {len(results)} | relevant returned {got} of {len(relevant)}")

    off_category = 0
    for n, r in enumerate(results[:10], start=1):
        cand = cand_of[r["resume_id"]]
        off_category += category[cand] != q["category"]
        facets = " ".join(f"{FACET_ABBR[k]}{v:.2f}" for k, v in r["facet_scores"].items())
        missing = sorted(r["missing_required"])[:4]
        print(f"{n:>2} {cand} g{truth.get(cand, 0)} | {category[cand][:26]:<26} | {r['label']} {r['raw_score'] * 100:.1f} | {facets} | miss {missing}")
    print(f"   off-category in top 10: {off_category}")

    for cand in relevant:
        rid = rid_of[cand]
        if rid in place:
            continue
        if rid not in retrieved:
            why = "not retrieved"
        elif rank_of[rid] > keep:
            why = f"cut by rerank (rank {rank_of[rid]})"
        elif not passed[rid]:
            why = "failed gate | " + gate_detail(resume_rows[rid], jd, work_rows[rid])
        else:
            why = "dropped after the gate (display threshold or result cap)"
        print(f"   MISSING {cand} grade {truth[cand]} | {category[cand]} | {why}")

    for cand in hard_negatives:
        rid = rid_of[cand]
        if rid in place:
            author_years = sum(w["duration_years"] for w in resumes[cand]["work_experience"])
            print(
                f"   LEAK {cand} ranked {place[rid]} | author data: grad {resumes[cand]['graduation_year']}, {author_years:.1f}y"
                f" | {gate_detail(resume_rows[rid], jd, work_rows[rid])}"
            )


def main():
    parser = argparse.ArgumentParser(description="Stage-by-stage audit of benchmark queries")
    parser.add_argument("query_ids", nargs="+")
    parser.add_argument("--row", default="baseline", help="ablation row whose patches to apply")
    args = parser.parse_args()
    if args.row not in ROWS:
        raise SystemExit(f"unknown row: {args.row}; choices: {list(ROWS)}")

    saved, resumes, queries = load()
    CONTEXT.update(author=resumes, cand_of={rid: cand for cand, rid in saved["resumes"].items()})
    memo.install()
    print(f"row: {args.row} ({ROWS[args.row][0]})\n")
    for qid in args.query_ids:
        with patched(ROWS[args.row][1]()):
            audit(qid, saved, resumes, queries)
        print()


if __name__ == "__main__":
    main()
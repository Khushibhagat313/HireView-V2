import argparse
import json
from contextlib import contextmanager

import src.retrieval.pipeline as pipeline
import src.scoring.eligibility as eligibility
import src.scoring.facets as facets
import src.scoring.skill_matcher as skill_matcher
from eval import memo
from eval.run_eval import MAP_PATH, PARSED_PATH, RESUMES_PATH, fmt, load_queries, prime_cache, run_query, summarize
from src.ingestion.normalizer import normalize_skills

OPTIONAL_FACETS = {"achievements_publications", "education_certifications"}
ORIGINAL_HYBRID = skill_matcher.hybrid_skill_score
ORIGINAL_FACET_QUERIES = facets.build_facet_queries


def years_in_any_job(_title, work):
    return sum(w.duration_years for w in work)


def no_years_check(_title, _work):
    return float("inf")


def composite_with_floored_optional(facet_scores):
    weights = facets.FACET_WEIGHTS
    total = sum(weights[f] for f in facet_scores)
    if total == 0:
        return {"composite_score": 0.0, "facet_scores": {}, "limited_data": True}
    core = {f: s for f, s in facet_scores.items() if f not in OPTIONAL_FACETS}
    floor = sum(s * weights[f] for f, s in core.items()) / sum(weights[f] for f in core) if core else 0.0
    effective = {f: (max(s, floor) if f in OPTIONAL_FACETS else s) for f, s in facet_scores.items()}
    score = sum(effective[f] * weights[f] / total for f in effective)
    return {"composite_score": score, "facet_scores": facet_scores, "limited_data": len(facet_scores) <= 1}


def hybrid_without_vacuous_overlap(candidate_skills, required_skills, preferred_skills, semantic_similarity):
    result = dict(ORIGINAL_HYBRID(candidate_skills, required_skills, preferred_skills, semantic_similarity))
    if not normalize_skills(required_skills):
        result["hybrid_score"] = semantic_similarity
    return result


def facet_queries_from_hyde(jd):
    queries = ORIGINAL_FACET_QUERIES(jd)
    hyde_vector = facets.embed_query(jd.hyde_text)
    queries["experience"] = hyde_vector
    queries["projects"] = hyde_vector
    return queries


NO_OPTIONAL_WEIGHT = {**facets.FACET_WEIGHTS, "achievements_publications": 0.0, "education_certifications": 0.0}

ROWS = {
    "baseline": ("current system", []),
    "gate-off": ("no years check (grad-year gate stays)", [(eligibility, "compute_field_specific_experience", no_years_check)]),
    "gate-total": ("years in any job instead of years in field", [(eligibility, "compute_field_specific_experience", years_in_any_job)]),
    "opt-floor": ("optional facets can't lower the score", [(pipeline, "compute_composite", composite_with_floored_optional)]),
    "opt-zero": ("optional facets weight 0", [(facets, "FACET_WEIGHTS", NO_OPTIONAL_WEIGHT)]),
    "skip-empty": ("no overlap term when nothing is required", [(pipeline, "hybrid_skill_score", hybrid_without_vacuous_overlap)]),
    "overlap-0.3": ("overlap weight 0.3 (now 0.6)", [(skill_matcher, "EXACT_OVERLAP_WEIGHT", 0.3)]),
    "overlap-0": ("overlap weight 0 (semantic only)", [(skill_matcher, "EXACT_OVERLAP_WEIGHT", 0.0)]),
    "hyde-facets": ("experience and projects facets use the HyDE text", [(pipeline, "build_facet_queries", facet_queries_from_hyde)]),
    "no-cutoff": ("score every retrieved resume (no rerank cut)", [(pipeline, "RERANK_KEEP_TOP_N", 1000)]),
    "no-cert": ("no cert boost", [(pipeline, "compute_max_cert_boost", lambda certs, jd: 1.0)]),
}
ROWS["combo"] = ("opt-floor + skip-empty + gate-total", ROWS["opt-floor"][1] + ROWS["skip-empty"][1] + ROWS["gate-total"][1])


@contextmanager
def patched(patches):
    originals = [(obj, name, getattr(obj, name)) for obj, name, _ in patches]
    for obj, name, value in patches:
        setattr(obj, name, value)
    try:
        yield
    finally:
        for obj, name, original in reversed(originals):
            setattr(obj, name, original)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rows", nargs="*", help="row names to run (default: all)")
    names = parser.parse_args().rows or list(ROWS)
    unknown = [n for n in names if n not in ROWS]
    if unknown:
        raise SystemExit(f"unknown rows: {unknown}; choices: {list(ROWS)}")

    queries = load_queries()
    saved = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    company_id = saved["company_id"]
    reverse = {rid: cand for cand, rid in saved["resumes"].items()}
    pool_skills = [normalize_skills(r["skills"]) for r in json.loads(RESUMES_PATH.read_text(encoding="utf-8"))]
    prime_cache(json.loads(PARSED_PATH.read_text(encoding="utf-8")))
    memo.install()

    for name in names:
        print(f"{name}: {ROWS[name][0]}")
    print()
    print(f"{'row':<14}{'recall@20':>10}{'mrr':>8}{'ndcg@10':>9}{'easy':>8}{'medium':>8}{'hard':>8}{'cov/ceil':>10}{'avg n':>7}")
    for name in names:
        with patched(ROWS[name][1]):
            rows = []
            for query in queries:
                rows.append(run_query(query, company_id, reverse, pool_skills, None))
                print(".", end="", flush=True)
        overall = summarize(rows)
        tier = {t: summarize([r for r in rows if r["difficulty"] == t])["ndcg_at_10"] for t in ("easy", "medium", "hard")}
        average_n = sum(r["results"] for r in rows) / len(rows)
        print(
            f"\r{name:<14}{fmt(overall['recall_at_20']):>10}{fmt(overall['mrr']):>8}{fmt(overall['ndcg_at_10']):>9}"
            f"{fmt(tier['easy']):>8}{fmt(tier['medium']):>8}{fmt(tier['hard']):>8}{fmt(overall['coverage_of_ceiling']):>10}{average_n:>7.1f}"
        )


if __name__ == "__main__":
    main()
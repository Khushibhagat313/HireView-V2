import argparse
import json
from contextlib import contextmanager

import src.retrieval.pipeline as pipeline
import src.scoring.eligibility as eligibility
import src.scoring.facets as facets
import src.scoring.skill_matcher as skill_matcher
from eval import memo
from eval.reading import tenure_score
from eval.run_eval import MAP_PATH, PARSED_PATH, RESUMES_PATH, fmt, load_queries, prime_cache, run_query, summarize
from src.embedding import embedder
from src.ingestion.normalizer import normalize_skills
from collections import defaultdict
import random

CONTEXT = {}
ORIGINAL_HYBRID = skill_matcher.hybrid_skill_score
ORIGINAL_FACET_QUERIES = facets.build_facet_queries


def static(*patches):
    return lambda: list(patches)


def combine(*factories):
    return lambda: [patch for factory in factories for patch in factory()]


def years_in_any_job(_title, work):
    return sum(w.duration_years for w in work)


def facet_queries_from_hyde(jd):
    queries = ORIGINAL_FACET_QUERIES(jd)
    hyde_vector = facets.embed_query(jd.hyde_text)
    queries["experience"] = hyde_vector
    queries["projects"] = hyde_vector
    return queries


def soft_skills(threshold):
    def factory():
        def hybrid(candidate_skills, required_skills, preferred_skills, semantic_similarity):
            result = dict(ORIGINAL_HYBRID(candidate_skills, required_skills, preferred_skills, semantic_similarity))
            required = normalize_skills(required_skills)
            held = normalize_skills(candidate_skills)
            missing = sorted(required - held)
            if not held or not missing:
                return result
            held_vectors = embedder.embed_documents(sorted(held))
            rescued = {
                skill
                for skill, vector in zip(missing, embedder.embed_documents(missing))
                if max(sum(x * y for x, y in zip(vector, other)) for other in held_vectors) >= threshold
            }
            if not rescued:
                return result
            matched = (held & required) | rescued
            weight = skill_matcher.EXACT_OVERLAP_WEIGHT
            result["hybrid_score"] = weight * len(matched) / len(required) + (1 - weight) * semantic_similarity
            result["matched_required"] = sorted(matched)
            result["missing_required"] = sorted(required - matched)
            return result

        return [(pipeline, "hybrid_skill_score", hybrid)]

    return factory


def rerank_blend(beta):
    def factory():
        original_rerank = pipeline.rerank
        original_filter = pipeline.filter_and_rank
        latest = {}

        def recording_rerank(company_id, text, ids):
            ranked = original_rerank(company_id, text, ids)
            latest.clear()
            latest.update({str(rid): score for rid, score in ranked})
            return ranked

        def blended_filter(results, threshold=None, max_results=None):
            if results:
                raws = [r["raw_score"] for r in results]
                scores = [latest[r["resume_id"]] for r in results]
                low, high = min(raws), max(raws)
                s_low, span = min(scores), (max(scores) - min(scores)) or 1.0
                results = [
                    {**r, "raw_score": (1 - beta) * r["raw_score"] + beta * (low + (high - low) * (s - s_low) / span)}
                    for r, s in zip(results, scores)
                ]
            return original_filter(results, threshold=threshold, max_results=max_results)

        return [(pipeline, "rerank", recording_rerank), (pipeline, "filter_and_rank", blended_filter)]

    return factory


def tenure_blend(alpha, by_type):
    def factory():
        original_queries = pipeline.build_facet_queries
        original_scores = pipeline.get_raw_facet_scores
        state = {}

        def recording_queries(jd):
            state["jd"] = jd
            return original_queries(jd)

        def scores_with_tenure(company_id, resume_id, facet_queries):
            scores = dict(original_scores(company_id, resume_id, facet_queries))
            entries = CONTEXT["author"][CONTEXT["cand_of"][str(resume_id)]]["work_experience"]
            tenure = tenure_score(entries, state["jd"].min_years_experience, by_type)
            if "experience" in scores and tenure is not None:
                scores["experience"] = (1 - alpha) * scores["experience"] + alpha * tenure
            return scores

        return [(pipeline, "build_facet_queries", recording_queries), (pipeline, "get_raw_facet_scores", scores_with_tenure)]

    return factory


GATE_TOTAL = static((eligibility, "compute_field_specific_experience", years_in_any_job))
HYDE_FACETS = static((pipeline, "build_facet_queries", facet_queries_from_hyde))
BLEND = rerank_blend(0.5)
SOFT = soft_skills(0.75)
TENURE = tenure_blend(0.5, True)

ROWS = {
    "baseline": ("adopted fixes only", static()),
    "soft-0.75": ("required skill counts as held if a listed skill is this close: 0.75", soft_skills(0.75)),
    "soft-0.80": ("same, 0.80", soft_skills(0.80)),
    "soft-0.85": ("same, 0.85", soft_skills(0.85)),
    "ce-0.3": ("rerank score blended into the final ranking, weight 0.3", rerank_blend(0.3)),
    "ce-0.5": ("same, weight 0.5", rerank_blend(0.5)),
    "ce-1.0": ("ranked by the rerank score alone, after the gate", rerank_blend(1.0)),
    "cut-10": ("rerank keeps the top 10", static((pipeline, "RERANK_KEEP_TOP_N", 10))),
    "cut-15": ("rerank keeps the top 15", static((pipeline, "RERANK_KEEP_TOP_N", 15))),
    "cut-30": ("rerank keeps the top 30", static((pipeline, "RERANK_KEEP_TOP_N", 30))),
    "gate-total": ("years in any job instead of years in field", GATE_TOTAL),
    "gate-total+ce-0.5": ("gate-total with the 0.5 rerank blend", combine(GATE_TOTAL, rerank_blend(0.5))),
    "hyde-facets": ("experience and projects facets use the HyDE text", HYDE_FACETS),
    "hyde-facets+ce-0.5": ("hyde-facets with the 0.5 rerank blend", combine(HYDE_FACETS, rerank_blend(0.5))),
    "tenure-0.3": ("experience facet 70% text, 30% tenure (all years count fully)", tenure_blend(0.3, False)),
    "tenure-type-0.3": ("same, freelance and internship years count half", tenure_blend(0.3, True)),
    "tenure-type-0.5": ("50% text, 50% tenure, freelance and internship years count half", tenure_blend(0.5, True)),
    "full": ("gate-total + rerank blend 0.5 + soft skills 0.75 + tenure/type 0.5", combine(GATE_TOTAL, BLEND, SOFT, TENURE)),
    "full-no-gate": ("full with the original title gate", combine(BLEND, SOFT, TENURE)),
    "full-no-ce": ("full without the rerank blend", combine(GATE_TOTAL, SOFT, TENURE)),
    "full-no-soft": ("full with exact skill matching only", combine(GATE_TOTAL, BLEND, TENURE)),
    "full-no-tenure": ("full with the experience facet as text only", combine(GATE_TOTAL, BLEND, SOFT)),
    "full-plain-tenure": ("full with tenure but no employment-type weighting", combine(GATE_TOTAL, BLEND, SOFT, tenure_blend(0.5, False))),
}


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


def pair_wins(queries, company_id, reverse):
    wins = 0
    for query in queries:
        if not query["query_id"].startswith("tech_backend_junior_"):
            continue
        ranked = [reverse[r["resume_id"]] for r in pipeline.search_and_score(company_id, query["jd_text"])]
        if "cand_01" in ranked and ("cand_06" not in ranked or ranked.index("cand_01") < ranked.index("cand_06")):
            wins += 1
    return wins


def by_category(scores, category_of):
    groups = defaultdict(list)
    for query_id, value in scores.items():
        groups[category_of[query_id]].append(value)
    return {category: sum(values) / len(values) for category, values in groups.items()}


def bootstrap_ci(values, draws=2000):
    rng = random.Random(0)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(draws))
    return means[int(0.025 * draws)], means[int(0.975 * draws)]


def compare(per_query, reference, others, category_of):
    reference_categories = by_category(per_query[reference], category_of)
    print(f"\nagainst {reference}: queries better/worse/same, categories better, mean nDCG change [95% CI], worst query")
    for name in others:
        deltas = {q: per_query[name][q] - per_query[reference][q] for q in per_query[name]}
        better = sum(d > 0.005 for d in deltas.values())
        worse = sum(d < -0.005 for d in deltas.values())
        categories = by_category(per_query[name], category_of)
        category_deltas = [categories[c] - reference_categories[c] for c in reference_categories]
        low, high = bootstrap_ci(category_deltas)
        worst_query, worst_delta = min(deltas.items(), key=lambda item: item[1])
        print(
            f"{name:<22}{f'{better}/{worse}/{len(deltas) - better - worse}':>10}"
            f"{f'{sum(d > 0.005 for d in category_deltas)}/{len(category_deltas)}':>7}"
            f"  {sum(category_deltas) / len(category_deltas):+.3f} [{low:+.3f}, {high:+.3f}]   {worst_query} {worst_delta:+.3f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rows", nargs="*", help="row names to run (default: all); the first is the reference for the comparison")
    names = parser.parse_args().rows or list(ROWS)
    unknown = [n for n in names if n not in ROWS]
    if unknown:
        raise SystemExit(f"unknown rows: {unknown}; choices: {list(ROWS)}")

    queries = load_queries()
    saved = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    company_id = saved["company_id"]
    reverse = {rid: cand for cand, rid in saved["resumes"].items()}
    author = {r["candidate_id"]: r for r in json.loads(RESUMES_PATH.read_text(encoding="utf-8"))}
    pool_skills = [normalize_skills(r["skills"]) for r in author.values()]
    CONTEXT.update(author=author, cand_of=reverse)
    prime_cache(json.loads(PARSED_PATH.read_text(encoding="utf-8")))
    memo.install()

    for name in names:
        print(f"{name}: {ROWS[name][0]}")
    print()
    print(f"{'row':<22}{'recall@20':>10}{'mrr':>8}{'ndcg@10':>9}{'easy':>8}{'medium':>8}{'hard':>8}{'cov/ceil':>10}{'avg n':>7}{'01>06':>7}")
    per_query = {}
    for name in names:
        with patched(ROWS[name][1]()):
            rows = []
            for query in queries:
                rows.append(run_query(query, company_id, reverse, pool_skills, None))
                print(".", end="", flush=True)
            wins = pair_wins(queries, company_id, reverse)
        per_query[name] = {r["query_id"]: r["ndcg_at_10"] or 0.0 for r in rows}
        overall = summarize(rows)
        tier = {t: summarize([r for r in rows if r["difficulty"] == t])["ndcg_at_10"] for t in ("easy", "medium", "hard")}
        average_n = sum(r["results"] for r in rows) / len(rows)
        print(
            f"\r{name:<22}{fmt(overall['recall_at_20']):>10}{fmt(overall['mrr']):>8}{fmt(overall['ndcg_at_10']):>9}"
            f"{fmt(tier['easy']):>8}{fmt(tier['medium']):>8}{fmt(tier['hard']):>8}{fmt(overall['coverage_of_ceiling']):>10}"
            f"{average_n:>7.1f}{f'{wins}/3':>7}"
        )

    categories = {q["query_id"]: q["category"] for q in queries}
    compare(per_query, names[0], names[1:], categories)
    if "full" in names and names[0] != "full":
        compare(per_query, "full", [n for n in names if n.startswith("full-")], categories)


if __name__ == "__main__":
    main()

import math


def _relevant(relevance: dict[str, int], min_grade: int = 1) -> set[str]:
    return {doc for doc, grade in relevance.items() if grade >= min_grade}


def recall_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int, min_grade: int = 1) -> float | None:
    relevant = _relevant(relevance, min_grade)
    if not relevant:
        return None
    return len(relevant & set(ranked_ids[:k])) / len(relevant)


def reciprocal_rank(ranked_ids: list[str], relevance: dict[str, int], min_grade: int = 1) -> float | None:
    relevant = _relevant(relevance, min_grade)
    if not relevant:
        return None
    for rank, doc in enumerate(ranked_ids, start=1):
        if doc in relevant:
            return 1 / rank
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float | None:
    ideal = sorted((g for g in relevance.values() if g > 0), reverse=True)[:k]
    if not ideal:
        return None
    dcg = sum(
        (2 ** relevance.get(doc, 0) - 1) / math.log2(rank + 1)
        for rank, doc in enumerate(ranked_ids[:k], start=1)
    )
    idcg = sum((2 ** grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal, start=1))
    return dcg / idcg


def skill_coverage_at_k(results: list[dict], required_skills: list[str], k: int) -> float | None:
    required = set(required_skills)
    if not required:
        return None
    coverages = [len(required & set(r["skills"])) / len(required) for r in results[:k]]
    return sum(coverages) / len(coverages) if coverages else None


def empty_rate(result_counts: list[int]) -> float:
    return sum(1 for n in result_counts if n == 0) / len(result_counts)


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = math.ceil(pct / 100 * len(ordered)) - 1
    return ordered[max(index, 0)]


def mean_defined(values: list[float | None]) -> float | None:
    defined = [v for v in values if v is not None]
    return sum(defined) / len(defined) if defined else None

def ceiling_coverage_at_k(pool_skills: list[set[str]], required_skills: set[str], k: int) -> float | None:
    required = set(required_skills)
    if not required:
        return None
    coverages = sorted((len(required & skills) / len(required) for skills in pool_skills), reverse=True)[:k]
    return sum(coverages) / len(coverages) if coverages else None
from src.config import DISPLAY_THRESHOLD, MAX_RESULTS

LABEL_THRESHOLDS = [
    (0.60, "Exceptional"),
    (0.50, "Strong"),
    (0.40, "Good"),
    (0.30, "Partial"),
]
DEFAULT_LABEL = "Weak"

def calibrate_score(raw_score: float) -> float:
    return min(raw_score * 100, 99.0)

def label_score(raw_score: float) -> str:
    for threshold, label in LABEL_THRESHOLDS:
        if raw_score >= threshold:
            return label
    return DEFAULT_LABEL

def filter_and_rank(scored_candidates: list[dict], threshold: float = None, max_results: int = None) -> list[dict]:
    threshold = DISPLAY_THRESHOLD if threshold is None else threshold
    max_results = MAX_RESULTS if max_results is None else max_results
    filtered = [c for c in scored_candidates if c["raw_score"] * 100 >= threshold]
    filtered.sort(key=lambda c: c["raw_score"], reverse=True)
    return filtered[:max_results]
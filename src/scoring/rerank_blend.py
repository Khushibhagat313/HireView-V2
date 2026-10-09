from src.scoring.calibration import calibrate_score, label_score


def blend_rerank_scores(results: list[dict], rerank_scores: dict[str, float], weight: float) -> list[dict]:
    if not results or weight == 0:
        return results

    raws = [r["raw_score"] for r in results]
    scores = [float(rerank_scores[r["resume_id"]]) for r in results]
    low, high = min(raws), max(raws)
    score_low = min(scores)
    span = (max(scores) - score_low) or 1.0

    blended = []
    for result, score in zip(results, scores):
        scaled = low + (high - low) * (score - score_low) / span
        raw_score = (1 - weight) * result["raw_score"] + weight * scaled
        blended.append(
            {
                **result,
                "raw_score": float(raw_score),
                "display_score": float(calibrate_score(raw_score)),
                "label": label_score(raw_score),
            }
        )
    return blended

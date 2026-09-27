from src.ingestion.normalizer import normalize_skills
from src.config import EXACT_OVERLAP_WEIGHT

def hybrid_skill_score(candidate_skills: list[str], required_skills: list[str], preferred_skills: list[str], semantic_similarity: float) -> dict:
    normalized_candidate = normalize_skills(candidate_skills)
    normalized_required = normalize_skills(required_skills)
    normalized_preferred = normalize_skills(preferred_skills)

    matched_required = normalized_candidate & normalized_required
    matched_preferred = normalized_candidate & normalized_preferred

    exact_overlap_ratio = len(matched_required) / len(normalized_required) if normalized_required else 1.0

    hybrid_score = EXACT_OVERLAP_WEIGHT * exact_overlap_ratio + (1 - EXACT_OVERLAP_WEIGHT) * semantic_similarity

    return {
        "hybrid_score": hybrid_score,
        "matched_required": sorted(matched_required),
        "missing_required": sorted(normalized_required - matched_required),
        "matched_preferred": sorted(matched_preferred),
    }
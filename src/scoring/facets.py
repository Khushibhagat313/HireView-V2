from src.embedding.embedder import embed_query
from src.db.store import get_resume_embeddings
from src.config import FACET_WEIGHTS

FACET_FIELD_TYPES = {
    "skills": ["skills"],
    "projects": ["projects"],
    "experience": ["experience"],
    "achievements_publications": ["achievements", "publications"],
    "education_certifications": ["education", "certifications"],
}

ACHIEVEMENT_QUERY_TEXT = "significant achievements, awards, honors, competition wins, published research, and notable recognition"

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    # Valid only because embed_documents/embed_query always return normalized
    # (unit-length) vectors — guarded by test_embedding_normalization in
    # tests/test_embedding.py. A dot product here is not a general cosine
    # similarity unless that holds.
    return sum(x * y for x, y in zip(a, b))

def _facet_query_text(jd, facet: str) -> str:
    if facet == "skills":
        return ", ".join(jd.required_skills + jd.preferred_skills)
    if facet == "projects":
        return ", ".join(jd.required_skills + jd.preferred_skills) + ". " + " ".join(jd.responsibilities)
    if facet == "experience":
        return " ".join(jd.responsibilities)
    if facet == "achievements_publications":
        return ACHIEVEMENT_QUERY_TEXT
    if facet == "education_certifications":
        parts = jd.required_skills + jd.preferred_skills + jd.responsibilities
        if jd.education_requirement:
            parts.append(jd.education_requirement)
        return ", ".join(parts)
    raise ValueError(f"No query text defined for facet: {facet}")

def build_facet_queries(jd) -> dict[str, list[float]]:
    return {facet: embed_query(_facet_query_text(jd, facet)) for facet in FACET_FIELD_TYPES}

def score_facets(company_id: str, resume_id: str, facet_queries: dict) -> dict:
    embeddings = get_resume_embeddings(company_id, resume_id)
    embeddings_by_type = {e.field_type: e.embedding for e in embeddings}

    facet_scores = {}
    for facet, field_types in FACET_FIELD_TYPES.items():
        present_types = [ft for ft in field_types if ft in embeddings_by_type]
        if not present_types:
            continue
        similarities = [_cosine_similarity(facet_queries[facet], embeddings_by_type[ft]) for ft in present_types]
        facet_scores[facet] = sum(similarities) / len(similarities)

    present_weight_total = sum(FACET_WEIGHTS[f] for f in facet_scores)
    if present_weight_total == 0:
        return {"composite_score": 0.0, "facet_scores": {}, "limited_data": True}

    composite_score = sum(
        facet_scores[f] * (FACET_WEIGHTS[f] / present_weight_total)
        for f in facet_scores
    )

    return {
        "composite_score": composite_score,
        "facet_scores": facet_scores,
        "limited_data": len(facet_scores) <= 1,
    }
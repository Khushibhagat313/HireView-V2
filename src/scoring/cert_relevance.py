from src.embedding.embedder import embed_query, embed_documents
from src.config import MAX_CERT_BOOST, CERT_RELEVANCE_FLOOR

def compute_cert_boost(cert, jd_requirements) -> float:
    if cert.tier != "assessed":
        return 1.0

    jd_text = ", ".join(jd_requirements.required_skills + jd_requirements.preferred_skills + jd_requirements.responsibilities)
    jd_vec = embed_query(jd_text)
    cert_vec = embed_documents([cert.name])[0]
    relevance = sum(x * y for x, y in zip(jd_vec, cert_vec))

    if relevance < CERT_RELEVANCE_FLOOR:
        return 1.0

    return 1 + (MAX_CERT_BOOST - 1) * relevance

def compute_max_cert_boost(certifications: list, jd_requirements) -> float:
    if not certifications:
        return 1.0
    return max(compute_cert_boost(cert, jd_requirements) for cert in certifications)
    
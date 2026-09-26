from src.embedding.embedder import embed_query, embed_documents
from src.config import FIELD_MATCH_THRESHOLD

def compute_field_specific_experience(jd_job_title: str, work_experience: list) -> float:
    if not work_experience:
        return 0.0
    target_vec = embed_query(jd_job_title)
    total = 0.0
    for entry in work_experience:
        title_vec = embed_documents([entry.title])[0]
        similarity = sum(x * y for x, y in zip(target_vec, title_vec))
        if similarity >= FIELD_MATCH_THRESHOLD:
            total += entry.duration_years
    return total

def check_eligibility(resume, jd_requirements, work_experience: list) -> bool:
    if not jd_requirements.min_years_experience:
        return True
    field_years = compute_field_specific_experience(jd_requirements.job_title, work_experience)
    return field_years >= jd_requirements.min_years_experience

from sentence_transformers import CrossEncoder
from src.config import RERANKER_MODEL
from src.db.store import get_resume

reranker = CrossEncoder(RERANKER_MODEL)

def _resume_text(resume) -> str:
    parts = [resume.summary_text, resume.skills_text, resume.projects_text, resume.experience_text]
    return " ".join(p for p in parts if p)

def rerank(company_id: str, query_text: str, resume_ids: set[str]) -> list[tuple[str, float]]:
    resumes = [get_resume(company_id, rid) for rid in resume_ids]
    pairs = [(query_text, _resume_text(r)) for r in resumes]
    scores = reranker.predict(pairs)
    return sorted(zip([r.id for r in resumes], scores), key=lambda x: x[1], reverse=True)
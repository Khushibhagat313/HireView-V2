from src.config import RETRIEVE_TOP_K
from src.db.store import search_by_vector

QUERY_FIELD_TYPES = {
    "skills": "skills",
    "experience": "experience",
    "projects": "projects",
    "hyde": "summary",
}

def search_candidates(company_id: str, queries: dict, job_posting_id: str = None) -> set[str]:
    resume_ids = set()
    for query_key, field_type in QUERY_FIELD_TYPES.items():
        vector = queries[query_key]
        results = search_by_vector(company_id, vector, field_type, RETRIEVE_TOP_K, job_posting_id=job_posting_id)
        for embedding, distance in results:
            resume_ids.add(str(embedding.resume_id))
    return resume_ids
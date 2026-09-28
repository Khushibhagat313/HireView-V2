from fastapi import APIRouter
from src.db.store import get_candidate

router = APIRouter()

@router.get("/candidates/{candidate_id}")
def get_candidate_route(candidate_id: str, company_id: str):
    candidate = get_candidate(company_id, candidate_id)
    return {
        "candidate_id": str(candidate.id),
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
    }
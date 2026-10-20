import hashlib
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.feedback import generate_feedback
from src.agents.interview_guide import GuideUnavailable, generate_interview_guide
from src.agents.jd_parser import parse_jd
from src.db.store import get_candidate
from src.retrieval.pipeline import search_and_score
from src.schemas.job import JDText

router = APIRouter()


@router.get("/candidates/{candidate_id}")
def get_candidate_route(candidate_id: UUID, company_id: UUID):
    candidate = get_candidate(str(company_id), str(candidate_id))
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {
        "candidate_id": str(candidate.id),
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
    }


class CandidateJDRequest(BaseModel):
    company_id: UUID
    jd_text: JDText


class FeedbackResponse(BaseModel):
    candidate_id: str
    feedback: str


class InterviewGuideResponse(BaseModel):
    candidate_id: str
    interview_guide: str


def _find_ranked_candidate(request: CandidateJDRequest, candidate_id: str) -> dict:
    for result in search_and_score(str(request.company_id), request.jd_text):
        if result["candidate_id"] == candidate_id:
            return result
    raise HTTPException(status_code=404, detail="Candidate is not among the ranked results for this job description")


# Groq outages (groq.APIError) are turned into 503 by the handler in main.py.
@router.post("/candidates/{candidate_id}/feedback", response_model=FeedbackResponse)
def candidate_feedback(candidate_id: UUID, request: CandidateJDRequest):
    candidate = _find_ranked_candidate(request, str(candidate_id))
    jd = parse_jd(request.jd_text)
    jd_hash = hashlib.sha256(request.jd_text.encode()).hexdigest()

    feedback = generate_feedback(str(request.company_id), jd_hash, jd, candidate)
    return {"candidate_id": str(candidate_id), "feedback": feedback}


@router.post("/candidates/{candidate_id}/interview-guide", response_model=InterviewGuideResponse)
def candidate_interview_guide(candidate_id: UUID, request: CandidateJDRequest):
    candidate = _find_ranked_candidate(request, str(candidate_id))
    jd = parse_jd(request.jd_text)
    jd_hash = hashlib.sha256(request.jd_text.encode()).hexdigest()

    try:
        guide = generate_interview_guide(str(request.company_id), jd_hash, jd, candidate)
    except GuideUnavailable:
        raise HTTPException(status_code=422, detail="No usable interview questions could be generated for this resume.")
    return {"candidate_id": str(candidate_id), "interview_guide": guide}

import hashlib

from fastapi import APIRouter, HTTPException
from groq import APIError
from pydantic import BaseModel

from src.agents.feedback import generate_feedback
from src.agents.interview_guide import GuideUnavailable, generate_interview_guide
from src.agents.jd_parser import parse_jd
from src.db.store import get_candidate
from src.retrieval.pipeline import search_and_score

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


class CandidateJDRequest(BaseModel):
    company_id: str
    jd_text: str


class FeedbackResponse(BaseModel):
    candidate_id: str
    feedback: str


class InterviewGuideResponse(BaseModel):
    candidate_id: str
    interview_guide: str


def _find_ranked_candidate(request: CandidateJDRequest, candidate_id: str) -> dict:
    for result in search_and_score(request.company_id, request.jd_text):
        if result["candidate_id"] == candidate_id:
            return result
    raise HTTPException(status_code=404, detail="Candidate is not among the ranked results for this job description")


@router.post("/candidates/{candidate_id}/feedback", response_model=FeedbackResponse)
def candidate_feedback(candidate_id: str, request: CandidateJDRequest):
    candidate = _find_ranked_candidate(request, candidate_id)
    jd = parse_jd(request.jd_text)
    jd_hash = hashlib.sha256(request.jd_text.encode()).hexdigest()

    try:
        feedback = generate_feedback(request.company_id, jd_hash, jd, candidate)
    except APIError:
        raise HTTPException(status_code=503, detail="The AI service is unavailable. Please try again.")
    return {"candidate_id": candidate_id, "feedback": feedback}


@router.post("/candidates/{candidate_id}/interview-guide", response_model=InterviewGuideResponse)
def candidate_interview_guide(candidate_id: str, request: CandidateJDRequest):
    candidate = _find_ranked_candidate(request, candidate_id)
    jd = parse_jd(request.jd_text)
    jd_hash = hashlib.sha256(request.jd_text.encode()).hexdigest()

    try:
        guide = generate_interview_guide(request.company_id, jd_hash, jd, candidate)
    except GuideUnavailable:
        raise HTTPException(status_code=422, detail="No usable interview questions could be generated for this resume.")
    except APIError:
        raise HTTPException(status_code=503, detail="The AI service is unavailable. Please try again.")
    return {"candidate_id": candidate_id, "interview_guide": guide}


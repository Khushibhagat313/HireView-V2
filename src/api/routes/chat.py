import hashlib

from fastapi import APIRouter
from pydantic import BaseModel
from src.agents.jd_parser import parse_jd

from src.retrieval.pipeline import search_and_score
from src.agents.conversation.graph import build_graph
from src.schemas.candidate import SearchResult


router = APIRouter()


class ChatRequest(BaseModel):
    company_id: str
    jd_text: str
    query: str


class ChatResponse(BaseModel):
    intent: str
    response_text: str | None
    response_candidates: list[SearchResult] | None


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    candidates = search_and_score(request.company_id, request.jd_text)
    jd_hash = hashlib.sha256(request.jd_text.encode()).hexdigest()

    app = build_graph()
    state = {
        "query": request.query,
        "company_id": request.company_id,
        "jd_hash": jd_hash,
        "jd": parse_jd(request.jd_text),
        "candidates": candidates,
        "below_threshold": [],
        "feedback_cache": {},
        "llm_calls": 0,
        "errors": [],
        "intent": None,
        "response_text": None,
        "response_candidates": None,
    }

    return app.invoke(state)
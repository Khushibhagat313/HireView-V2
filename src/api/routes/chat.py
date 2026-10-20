import hashlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, StringConstraints
from src.agents.jd_parser import parse_jd

from src.config import MAX_QUESTION_CHARS
from src.retrieval.pipeline import search_and_score
from src.agents.conversation.graph import build_graph
from src.schemas.candidate import SearchResult
from src.schemas.job import JDText


router = APIRouter()

# Compiled once: the graph is the same for every question.
graph = build_graph()


class ChatRequest(BaseModel):
    company_id: UUID
    jd_text: JDText
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_CHARS)]


class ChatResponse(BaseModel):
    intent: str
    response_text: str | None
    response_candidates: list[SearchResult] | None


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    candidates = search_and_score(str(request.company_id), request.jd_text)
    jd_hash = hashlib.sha256(request.jd_text.encode()).hexdigest()

    state = {
        "query": request.query,
        "company_id": str(request.company_id),
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

    return graph.invoke(state)

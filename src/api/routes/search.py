from fastapi import APIRouter
from pydantic import BaseModel
from src.retrieval.pipeline import search_and_score
from src.schemas.candidate import SearchResult


router = APIRouter()

class SearchRequest(BaseModel):
    company_id: str
    jd_text: str
    job_posting_id: str | None = None
    threshold: float | None = None
    max_results: int | None = None

class SearchResponse(BaseModel):
    results: list[SearchResult]

@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    results = search_and_score(
        request.company_id,
        request.jd_text,
        job_posting_id=request.job_posting_id,
        threshold=request.threshold,
        max_results=request.max_results,
    )
    return {"results": results}
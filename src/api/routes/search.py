from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field
from src.retrieval.pipeline import search_and_score
from src.schemas.candidate import SearchResult
from src.schemas.job import JDText


router = APIRouter()

class SearchRequest(BaseModel):
    company_id: UUID
    jd_text: JDText
    job_posting_id: UUID | None = None
    threshold: float | None = Field(None, ge=0, le=100)
    max_results: int | None = Field(None, ge=1, le=100)

class SearchResponse(BaseModel):
    results: list[SearchResult]

@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    results = search_and_score(
        str(request.company_id),
        request.jd_text,
        job_posting_id=str(request.job_posting_id) if request.job_posting_id else None,
        threshold=request.threshold,
        max_results=request.max_results,
    )
    return {"results": results}

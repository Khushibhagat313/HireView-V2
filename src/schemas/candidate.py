from pydantic import BaseModel


class SearchResult(BaseModel):
    resume_id: str
    candidate_id: str
    candidate_name: str
    raw_score: float
    display_score: float
    label: str
    facet_scores: dict[str, float]
    limited_data: bool
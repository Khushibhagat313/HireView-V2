from pydantic import BaseModel, ConfigDict


class WorkExperienceItem(BaseModel):
    # pipeline passes SimpleNamespace objects, not dicts
    model_config = ConfigDict(from_attributes=True)

    title: str
    duration_years: float


class SearchResult(BaseModel):
    resume_id: str
    candidate_id: str
    candidate_name: str
    raw_score: float
    display_score: float
    label: str
    facet_scores: dict[str, float]
    limited_data: bool
    skills: list[str] = []
    matched_required: list[str] = []
    missing_required: list[str] = []
    matched_preferred: list[str] = []
    work_experience: list[WorkExperienceItem] = []

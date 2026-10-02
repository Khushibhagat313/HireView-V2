from typing import TypedDict
from src.schemas.job import JDRequirements


class HiringState(TypedDict):
    company_id: str
    jd_hash: str
    jd: JDRequirements | None
    candidates: list[dict]
    below_threshold: list[dict]
    feedback_cache: dict[str, str]
    llm_calls: int
    errors: list[str]
    query: str
    intent: str | None
    response_text: str | None
    response_candidates: list[dict] | None
                                                                                                                                                                                                         

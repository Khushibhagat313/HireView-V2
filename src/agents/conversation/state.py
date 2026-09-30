from typing import TypedDict


class HiringState(TypedDict):
    company_id: str
    jd_hash: str
    candidates: list[dict]
    below_threshold: list[dict]
    feedback_cache: dict[str, str]
    llm_calls: int
    errors: list[str]
    query: str
    intent: str | None
    response_text: str | None
    response_candidates: list[dict] | None
                                                                                                                                                                                                         

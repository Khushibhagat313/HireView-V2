from typing import Annotated

from pydantic import BaseModel, StringConstraints

from src.config import MAX_JD_CHARS

# A job description as the API accepts it: blank text would only waste an AI call,
# and an oversized one fails at the AI with a vaguer error.
JDText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_JD_CHARS)]

class JDRequirements(BaseModel):
    job_title: str
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    responsibilities: list[str] = []
    min_years_experience: float | None = None
    education_requirement: str | None = None
    eligible_graduation_years: list[int] = []
    hyde_text: str

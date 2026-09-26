from pydantic import BaseModel

class JDRequirements(BaseModel):
    job_title: str
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    responsibilities: list[str] = []
    min_years_experience: float | None = None
    education_requirement: str | None = None
    hyde_text: str
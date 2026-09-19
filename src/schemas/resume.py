from pydantic import BaseModel, field_validator

class Certification(BaseModel):
    name: str
    issuer: str | None = None
    tier: str  # "assessed" or "completion"

class ResumeLink(BaseModel):
    link_type: str  # github, live_demo, portfolio, linkedin, other
    url: str
    label: str | None = None

class SectionedResume(BaseModel):
    candidate_name: str
    candidate_email: str
    candidate_phone: str | None = None
    summary_text: str | None = None
    skills_text: str | None = None
    projects_text: str | None = None
    experience_text: str | None = None
    achievements_text: str | None = None
    publications_text: str | None = None
    education_text: str | None = None
    certifications_text: str | None = None
    certifications: list[Certification] = []
    links: list[ResumeLink] = []
    skills: list[str] = []
    years_experience: float | None = None

    @field_validator("years_experience")
    @classmethod
    def clamp_years(cls, v):
        if v is None:
            return v
        return max(0.0, min(v, 40.0))
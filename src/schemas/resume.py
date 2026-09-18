from pydantic import BaseModel

class Certification(BaseModel):
    name: str
    issuer: str | None = None
    tier: str  # "assessed" or "completion"

class ResumeLink(BaseModel):
    link_type: str  # github, live_demo, portfolio, linkedin, other
    url: str
    label: str | None = None

class SectionedResume(BaseModel):
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
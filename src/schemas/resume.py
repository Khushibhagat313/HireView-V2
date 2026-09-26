from pydantic import BaseModel, model_validator

class Certification(BaseModel):
    name: str
    issuer: str | None = None
    tier: str  # "assessed" or "completion"

class ResumeLink(BaseModel):
    link_type: str  # github, live_demo, portfolio, linkedin, other
    url: str
    label: str | None = None

class WorkExperienceEntry(BaseModel):
    title: str
    company_name: str | None = None
    duration_years: float

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
    work_experience: list[WorkExperienceEntry] = []
    years_experience: float = 0.0

    @model_validator(mode="after")
    def compute_years_experience(self):
        self.years_experience = min(sum(w.duration_years for w in self.work_experience), 40.0)
        return self
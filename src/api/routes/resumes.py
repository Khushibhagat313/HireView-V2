from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from src.ingestion.pipeline import ingest_resume
from src.db.store import delete_resume, get_company, get_job_posting, list_resumes
from src.retrieval.pipeline import invalidate_search_cache

router = APIRouter()


class ResumeSummary(BaseModel):
    resume_id: str
    candidate_id: str
    candidate_name: str
    candidate_email: str
    skills: list[str]
    years_experience: float | None
    uploaded_at: datetime


class ResumeListResponse(BaseModel):
    resumes: list[ResumeSummary]


@router.get("/resumes", response_model=ResumeListResponse)
def list_resumes_route(company_id: UUID):
    rows = list_resumes(str(company_id))
    return {"resumes": [
        {
            "resume_id": str(resume.id),
            "candidate_id": str(candidate.id),
            "candidate_name": candidate.name,
            "candidate_email": candidate.email,
            "skills": sorted(resume.skills or []),
            "years_experience": resume.years_experience,
            "uploaded_at": resume.created_at,
        }
        for resume, candidate in rows
    ]}


@router.post("/resumes/upload", status_code=201)
def upload_resume(company_id: UUID = Form(...), file: UploadFile = File(...), job_posting_id: UUID | None = Form(None)):
    # checked up front: otherwise the ~20s ingestion runs first and then fails on the foreign key
    if get_company(str(company_id)) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if job_posting_id and get_job_posting(str(company_id), str(job_posting_id)) is None:
        raise HTTPException(status_code=404, detail="Job posting not found")

    pdf_bytes = file.file.read()
    resume_id = ingest_resume(str(company_id), pdf_bytes, job_posting_id=str(job_posting_id) if job_posting_id else None)
    invalidate_search_cache(str(company_id))
    return {"resume_id": resume_id}

@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume_route(resume_id: UUID, company_id: UUID):
    if not delete_resume(str(company_id), str(resume_id)):
        raise HTTPException(status_code=404, detail="Resume not found")
    invalidate_search_cache(str(company_id))

from fastapi import APIRouter, UploadFile, File, Form
from src.ingestion.pipeline import ingest_resume
from src.db.store import delete_resume

router = APIRouter()

@router.post("/resumes/upload", status_code=201)
def upload_resume(company_id: str = Form(...), file: UploadFile = File(...), job_posting_id: str = Form(None)):
    pdf_bytes = file.file.read()
    resume_id = ingest_resume(company_id, pdf_bytes, job_posting_id=job_posting_id)
    return {"resume_id": resume_id}

@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume_route(resume_id: str, company_id: str):
    delete_resume(company_id, resume_id)
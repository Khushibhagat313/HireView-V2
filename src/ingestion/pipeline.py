from src.ingestion.guards import check_is_pdf, check_size, check_pages, is_scanned
from src.ingestion.extractor import extract_text
from src.ingestion.sectioner import split_sections
from src.ingestion.normalizer import normalize_skills
from src.embedding.embedder import embed_documents
from src.db.store import save_ingested_resume

FIELD_TYPES = [
    "summary_text",
    "skills_text",
    "projects_text",
    "experience_text",
    "achievements_text",
    "publications_text",
    "education_text",
    "certifications_text",
]


def store_sectioned_resume(company_id: str, sectioned, job_posting_id: str = None, expires_at=None) -> str:
    normalized_skills = list(normalize_skills(sectioned.skills))

    # All the slow work (parsing, embedding) happens before anything touches the database.
    sections = [(field_type, getattr(sectioned, field_type)) for field_type in FIELD_TYPES]
    sections = [(field_type, section) for field_type, section in sections if section]
    vectors = embed_documents([section for _, section in sections]) if sections else []
    embeddings = [(field_type.replace("_text", ""), vector) for (field_type, _), vector in zip(sections, vectors)]

    resume_data = {
        "source": "upload",
        "summary_text": sectioned.summary_text,
        "skills_text": sectioned.skills_text,
        "projects_text": sectioned.projects_text,
        "experience_text": sectioned.experience_text,
        "achievements_text": sectioned.achievements_text,
        "publications_text": sectioned.publications_text,
        "education_text": sectioned.education_text,
        "certifications_text": sectioned.certifications_text,
        "years_experience": sectioned.years_experience,
        "graduation_year": sectioned.graduation_year,
        "skills": normalized_skills,
        "expires_at": expires_at,
    }

    return save_ingested_resume(
        company_id,
        candidate={"name": sectioned.candidate_name, "email": sectioned.candidate_email, "phone": sectioned.candidate_phone},
        resume_data=resume_data,
        embeddings=embeddings,
        certifications=[{"name": c.name, "issuer": c.issuer, "tier": c.tier} for c in sectioned.certifications],
        links=[{"link_type": l.link_type, "url": l.url, "label": l.label} for l in sectioned.links],
        work_experience=[
            {"title": w.title, "company_name": w.company_name, "duration_years": w.duration_years}
            for w in sectioned.work_experience
        ],
        job_posting_id=job_posting_id,
    )


def ingest_resume(company_id: str, pdf_bytes: bytes, job_posting_id: str = None, expires_at=None) -> str:
    check_size(pdf_bytes)
    check_is_pdf(pdf_bytes)
    check_pages(pdf_bytes)
    is_scanned(pdf_bytes)

    text = extract_text(pdf_bytes)
    sectioned = split_sections(text)
    return store_sectioned_resume(company_id, sectioned, job_posting_id=job_posting_id, expires_at=expires_at)

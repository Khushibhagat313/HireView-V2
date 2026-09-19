from src.ingestion.guards import check_size, check_pages, is_scanned
from src.ingestion.extractor import extract_text
from src.ingestion.sectioner import split_sections
from src.ingestion.normalizer import normalize_skills
from src.embedding.embedder import embed_documents
from src.db.store import add_candidate, add_resume, add_resume_embedding, add_certification, add_resume_link

FIELD_TYPES = [
    "summary_text", "skills_text", "projects_text", "experience_text",
    "achievements_text", "publications_text", "education_text", "certifications_text",
]

def ingest_resume(company_id: str, pdf_bytes: bytes, expires_at=None) -> str:
    check_size(pdf_bytes)
    check_pages(pdf_bytes)
    is_scanned(pdf_bytes)

    text = extract_text(pdf_bytes)
    sectioned = split_sections(text)
    normalized_skills = list(normalize_skills(sectioned.skills))

    candidate = add_candidate(company_id, sectioned.candidate_name, sectioned.candidate_email, sectioned.candidate_phone)

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
        "skills": normalized_skills,
        "expires_at": expires_at,
    }
    resume = add_resume(company_id, candidate.id, resume_data)

    for field_type in FIELD_TYPES:
        section_text = getattr(sectioned, field_type)
        if section_text:
            vector = embed_documents([section_text])[0]
            add_resume_embedding(company_id, resume.id, field_type.replace("_text", ""), vector)

    for cert in sectioned.certifications:
        add_certification(company_id, resume.id, cert.name, cert.issuer, cert.tier)

    for link in sectioned.links:
        add_resume_link(company_id, resume.id, link.link_type, link.url, link.label)

    return str(resume.id)
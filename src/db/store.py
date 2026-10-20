from contextlib import contextmanager
from sqlalchemy import func
from src.db.session import get_session
from src.db.models import Company, Candidate, Resume, ResumeEmbedding, Certification, ResumeLink, JobPosting, Application, WorkExperience

get_session_ctx = contextmanager(get_session)


def create_company(name: str) -> Company:
    with get_session_ctx() as session:
        company = Company(name=name)
        session.add(company)
        session.commit()
        session.refresh(company)
        return company

def add_candidate(company_id: str, name: str, email: str, phone: str = None) -> Candidate:
    with get_session_ctx() as session:
        existing = session.query(Candidate).filter_by(company_id=company_id, email=email).first()
        if existing:
            existing.name = name
            existing.phone = phone
            session.commit()
            session.refresh(existing)
            return existing
        candidate = Candidate(company_id=company_id, name=name, email=email, phone=phone)
        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        return candidate       

def add_resume(company_id: str, candidate_id: str, resume_data: dict) -> Resume:
    with get_session_ctx() as session:
        resume = Resume(company_id=company_id, candidate_id=candidate_id, **resume_data)
        session.add(resume)
        session.commit()
        session.refresh(resume)
        return resume        

def save_ingested_resume(
    company_id: str,
    candidate: dict,
    resume_data: dict,
    embeddings: list[tuple[str, list[float]]],
    certifications: list[dict],
    links: list[dict],
    work_experience: list[dict],
    job_posting_id: str = None,
) -> str:
    # One transaction for the whole resume: if any row fails, none are kept,
    # so a failed upload never leaves a resume without its embeddings or experience.
    with get_session_ctx() as session:
        try:
            # Case-insensitive: Priya@x.com and priya@x.com are the same person.
            person = (
                session.query(Candidate)
                .filter(Candidate.company_id == company_id, func.lower(Candidate.email) == candidate["email"].strip().lower())
                .first()
            )
            if person:
                person.name = candidate["name"]
                person.phone = candidate.get("phone")
            else:
                person = Candidate(company_id=company_id, name=candidate["name"], email=candidate["email"], phone=candidate.get("phone"))
                session.add(person)
            session.flush()

            resume = Resume(company_id=company_id, candidate_id=person.id, **resume_data)
            session.add(resume)
            session.flush()

            if job_posting_id:
                session.add(Application(company_id=company_id, job_posting_id=job_posting_id, candidate_id=person.id, resume_id=resume.id))
            session.add_all(
                [ResumeEmbedding(company_id=company_id, resume_id=resume.id, field_type=field_type, embedding=vector) for field_type, vector in embeddings]
                + [Certification(company_id=company_id, resume_id=resume.id, **cert) for cert in certifications]
                + [ResumeLink(company_id=company_id, resume_id=resume.id, **link) for link in links]
                + [WorkExperience(company_id=company_id, resume_id=resume.id, **entry) for entry in work_experience]
            )
            session.commit()
            return str(resume.id)
        except Exception:
            session.rollback()
            raise

def add_resume_embedding(company_id: str, resume_id: str, field_type: str, vector: list[float]) -> ResumeEmbedding:
    with get_session_ctx() as session:
        embedding = ResumeEmbedding(company_id=company_id, resume_id=resume_id, field_type=field_type, embedding=vector)
        session.add(embedding)
        session.commit()
        session.refresh(embedding)
        return embedding

def delete_resume(company_id: str, resume_id: str) -> bool:
    with get_session_ctx() as session:
        resume = session.query(Resume).filter_by(id=resume_id, company_id=company_id).first()
        if resume is None:
            return False
        candidate_id = resume.candidate_id
        session.delete(resume)
        session.flush()
        # Their last resume is gone, so drop their name, email and phone too.
        if session.query(Resume).filter_by(candidate_id=candidate_id).first() is None:
            session.query(Candidate).filter_by(id=candidate_id).delete()
        session.commit()
        return True

def get_resume(company_id: str, resume_id: str) -> Resume | None:
    with get_session_ctx() as session:
        return session.query(Resume).filter_by(id=resume_id, company_id=company_id).first()


def get_resume_embeddings(company_id: str, resume_id: str) -> list[ResumeEmbedding]:
    with get_session_ctx() as session:
        return session.query(ResumeEmbedding).filter_by(resume_id=resume_id, company_id=company_id).all() 

def add_certification(company_id: str, resume_id: str, name: str, issuer: str, tier: str) -> Certification:
    with get_session_ctx() as session:
        cert = Certification(company_id=company_id, resume_id=resume_id, name=name, issuer=issuer, tier=tier)
        session.add(cert)
        session.commit()
        session.refresh(cert)
        return cert


def add_resume_link(company_id: str, resume_id: str, link_type: str, url: str, label: str = None) -> ResumeLink:
    with get_session_ctx() as session:
        link = ResumeLink(company_id=company_id, resume_id=resume_id, link_type=link_type, url=url, label=label)
        session.add(link)
        session.commit()
        session.refresh(link)
        return link        

def search_by_vector(company_id: str, vector: list[float], field_type: str, k: int, job_posting_id: str = None) -> list[tuple]:
    with get_session_ctx() as session:
        distance = ResumeEmbedding.embedding.cosine_distance(vector)
        query = session.query(ResumeEmbedding, distance.label("distance")).filter(
            ResumeEmbedding.company_id == company_id,
            ResumeEmbedding.field_type == field_type,
        )
        if job_posting_id:
            query = query.join(Application, Application.resume_id == ResumeEmbedding.resume_id).filter(
                Application.job_posting_id == job_posting_id
            )
        results = query.order_by(distance).limit(k).all()
        return [(row[0], row[1]) for row in results]


def delete_company(company_id: str) -> None:
    with get_session_ctx() as session:
        company = session.get(Company, company_id)
        session.delete(company)
        session.commit()

def add_job_posting(company_id: str, title: str, raw_text: str) -> JobPosting:
    with get_session_ctx() as session:
        posting = JobPosting(company_id=company_id, title=title, raw_text=raw_text)
        session.add(posting)
        session.commit()
        session.refresh(posting)
        return posting


def add_application(company_id: str, job_posting_id: str, candidate_id: str, resume_id: str) -> Application:
    with get_session_ctx() as session:
        application = Application(company_id=company_id, job_posting_id=job_posting_id, candidate_id=candidate_id, resume_id=resume_id)
        session.add(application)
        session.commit()
        session.refresh(application)
        return application
    
def add_work_experience(company_id: str, resume_id: str, title: str, company_name: str, duration_years: float) -> WorkExperience:
    with get_session_ctx() as session:
        entry = WorkExperience(company_id=company_id, resume_id=resume_id, title=title, company_name=company_name, duration_years=duration_years)
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry

def get_work_experiences(company_id: str, resume_id: str) -> list[WorkExperience]:
    with get_session_ctx() as session:
        return session.query(WorkExperience).filter_by(resume_id=resume_id, company_id=company_id).all()

def get_certifications(company_id: str, resume_id: str) -> list[Certification]:
    with get_session_ctx() as session:
        return session.query(Certification).filter_by(resume_id=resume_id, company_id=company_id).all()

def get_candidate(company_id: str, candidate_id: str) -> Candidate | None:
    with get_session_ctx() as session:
        return session.query(Candidate).filter_by(id=candidate_id, company_id=company_id).first()

def get_resumes(company_id: str, resume_ids: list[str]) -> dict[str, Resume]:
    with get_session_ctx() as session:
        rows = session.query(Resume).filter(Resume.company_id == company_id, Resume.id.in_(resume_ids)).all()
        return {str(row.id): row for row in rows}


def get_work_experiences_many(company_id: str, resume_ids: list[str]) -> dict[str, list[WorkExperience]]:
    with get_session_ctx() as session:
        rows = session.query(WorkExperience).filter(
            WorkExperience.company_id == company_id, WorkExperience.resume_id.in_(resume_ids)
        ).all()
        grouped = {str(rid): [] for rid in resume_ids}
        for row in rows:
            grouped[str(row.resume_id)].append(row)
        return grouped


def get_certifications_many(company_id: str, resume_ids: list[str]) -> dict[str, list[Certification]]:
    with get_session_ctx() as session:
        rows = session.query(Certification).filter(
            Certification.company_id == company_id, Certification.resume_id.in_(resume_ids)
        ).all()
        grouped = {str(rid): [] for rid in resume_ids}
        for row in rows:
            grouped[str(row.resume_id)].append(row)
        return grouped


def get_candidates(company_id: str, candidate_ids: list[str]) -> dict[str, Candidate]:
    with get_session_ctx() as session:
        rows = session.query(Candidate).filter(Candidate.company_id == company_id, Candidate.id.in_(candidate_ids)).all()
        return {str(row.id): row for row in rows}


def get_company(company_id: str) -> Company | None:
    with get_session_ctx() as session:
        return session.get(Company, company_id)


def get_job_posting(company_id: str, job_posting_id: str) -> JobPosting | None:
    with get_session_ctx() as session:
        return session.query(JobPosting).filter_by(id=job_posting_id, company_id=company_id).first()


def list_resumes(company_id: str) -> list[tuple[Resume, Candidate]]:
    with get_session_ctx() as session:
        return (
            session.query(Resume, Candidate)
            .join(Candidate, Candidate.id == Resume.candidate_id)
            .filter(Resume.company_id == company_id)
            .order_by(Resume.created_at.desc())
            .all()
        )

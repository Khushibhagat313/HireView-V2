from contextlib import contextmanager
from src.db.session import get_session
from src.db.models import Company, Candidate, Resume, ResumeEmbedding, Certification, ResumeLink

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

def add_resume_embedding(company_id: str, resume_id: str, field_type: str, vector: list[float]) -> ResumeEmbedding:
    with get_session_ctx() as session:
        embedding = ResumeEmbedding(company_id=company_id, resume_id=resume_id, field_type=field_type, embedding=vector)
        session.add(embedding)
        session.commit()
        session.refresh(embedding)
        return embedding

def delete_resume(company_id: str, resume_id: str) -> None:
    with get_session_ctx() as session:
        resume = session.query(Resume).filter_by(id=resume_id, company_id=company_id).first()
        session.delete(resume)
        session.commit()

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


from src.db.store import (
    add_candidate,
    add_resume,
    add_resume_embedding,
    delete_resume,
    get_candidate,
    get_resume,
    get_resume_embeddings,
    save_ingested_resume,
)


def test_insert_and_read_back(make_company):
    company = make_company("Pytest Co")
    candidate = add_candidate(company.id, "Test Candidate", "testcand@example.com")
    resume = add_resume(company.id, candidate.id, {"source": "upload", "skills_text": "Python"})
    embedding = add_resume_embedding(company.id, resume.id, "skills", [0.0] * 384)

    assert resume.company_id == company.id
    assert embedding.resume_id == resume.id


def test_cascade_delete(make_company):
    company = make_company("Pytest Co 2")
    candidate = add_candidate(company.id, "Cascade Candidate", "cascade@example.com")
    resume = add_resume(company.id, candidate.id, {"source": "upload"})
    add_resume_embedding(company.id, resume.id, "skills", [0.0] * 384)

    delete_resume(company.id, resume.id)

    assert get_resume(company.id, resume.id) is None
    assert get_resume_embeddings(company.id, resume.id) == []

def test_tenant_isolation(make_company):
    company_a = make_company("Company A")
    company_b = make_company("Company B")
    candidate_a = add_candidate(company_a.id, "Candidate A", "a@example.com")
    resume_a = add_resume(company_a.id, candidate_a.id, {"source": "upload"})

    assert get_resume(company_b.id, resume_a.id) is None
    assert get_resume(company_a.id, resume_a.id) is not None  

def test_same_email_two_companies(make_company):
    company_a = make_company("Company C")
    company_b = make_company("Company D")

    candidate_a = add_candidate(company_a.id, "Same Name", "same@example.com")
    candidate_b = add_candidate(company_b.id, "Same Name", "same@example.com")

    assert candidate_a.id != candidate_b.id
    assert candidate_a.company_id != candidate_b.company_id


def test_deleting_last_resume_removes_the_candidate(make_company):
    company = make_company("Pytest Co 3")
    candidate = add_candidate(company.id, "Two Versions", "two@example.com")
    old = add_resume(company.id, candidate.id, {"source": "upload"})
    new = add_resume(company.id, candidate.id, {"source": "upload"})

    delete_resume(company.id, old.id)
    assert get_candidate(company.id, candidate.id) is not None  # still has a resume

    delete_resume(company.id, new.id)
    assert get_candidate(company.id, candidate.id) is None


def test_reupload_matches_email_regardless_of_case(make_company):
    company = make_company("Pytest Co 4")
    empty = dict(embeddings=[], certifications=[], links=[], work_experience=[])
    first = save_ingested_resume(company.id, {"name": "Priya", "email": "Priya@Example.com"}, {"source": "upload"}, **empty)
    second = save_ingested_resume(company.id, {"name": "Priya", "email": "priya@example.com"}, {"source": "upload"}, **empty)

    assert get_resume(company.id, first).candidate_id == get_resume(company.id, second).candidate_id


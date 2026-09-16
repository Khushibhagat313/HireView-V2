from src.db.store import create_company, add_candidate, add_resume, add_resume_embedding, delete_resume, get_resume, get_resume_embeddings


def test_insert_and_read_back():
    company = create_company("Pytest Co")
    candidate = add_candidate(company.id, "Test Candidate", "testcand@example.com")
    resume = add_resume(company.id, candidate.id, {"source": "upload", "skills_text": "Python"})
    embedding = add_resume_embedding(company.id, resume.id, "skills", [0.0] * 384)

    assert resume.company_id == company.id
    assert embedding.resume_id == resume.id


def test_cascade_delete():
    company = create_company("Pytest Co 2")
    candidate = add_candidate(company.id, "Cascade Candidate", "cascade@example.com")
    resume = add_resume(company.id, candidate.id, {"source": "upload"})
    add_resume_embedding(company.id, resume.id, "skills", [0.0] * 384)

    delete_resume(company.id, resume.id)

    assert get_resume(company.id, resume.id) is None
    assert get_resume_embeddings(company.id, resume.id) == []

def test_tenant_isolation():
    company_a = create_company("Company A")
    company_b = create_company("Company B")
    candidate_a = add_candidate(company_a.id, "Candidate A", "a@example.com")
    resume_a = add_resume(company_a.id, candidate_a.id, {"source": "upload"})

    assert get_resume(company_b.id, resume_a.id) is None
    assert get_resume(company_a.id, resume_a.id) is not None  

def test_same_email_two_companies():
    company_a = create_company("Company C")
    company_b = create_company("Company D")

    candidate_a = add_candidate(company_a.id, "Same Name", "same@example.com")
    candidate_b = add_candidate(company_b.id, "Same Name", "same@example.com")

    assert candidate_a.id != candidate_b.id
    assert candidate_a.company_id != candidate_b.company_id
import math
import pytest
from src.embedding.embedder import embed_documents, embed_query, model
from src.ingestion.pipeline import ingest_resume
from src.ingestion.extractor import extract_text
from src.ingestion.sectioner import split_sections
from src.db.models import Candidate
from src.db.store import get_resume, get_resume_embeddings, get_session_ctx, list_resumes, search_by_vector


def test_storage_round_trip(make_company):
    company = make_company("Storage Round Trip Co")
    resume_id = ingest_resume(company.id, open("tests/Priya_Sharma_Resume_sample.pdf", "rb").read())
    resume = get_resume(company.id, resume_id)
    embeddings = get_resume_embeddings(company.id, resume_id)

    assert resume is not None
    assert resume.years_experience == 0.25
    assert "pgvector" in resume.skills
    assert len(embeddings) == 6


def test_failed_ingestion_saves_nothing(make_company, monkeypatch):
    # A vector of the wrong size makes the embedding insert fail after the candidate and resume rows
    # were already written in the same transaction; all of them must be rolled back.
    company = make_company("Rollback Co")
    monkeypatch.setattr("src.ingestion.pipeline.embed_documents", lambda texts: [[0.1, 0.2, 0.3] for _ in texts])

    with pytest.raises(Exception):
        ingest_resume(company.id, open("tests/Priya_Sharma_Resume_sample.pdf", "rb").read())

    assert list_resumes(company.id) == []
    with get_session_ctx() as session:
        assert session.query(Candidate).filter_by(company_id=company.id).count() == 0


def test_embedding_normalization():
    vectors = embed_documents(["Sample text for normalization check"])
    magnitude = math.sqrt(sum(x * x for x in vectors[0]))
    assert abs(magnitude - 1.0) < 1e-4


@pytest.fixture(scope="module")
def sectioned_priya():
    text = extract_text(open("tests/Priya_Sharma_Resume_sample.pdf", "rb").read())
    return split_sections(text)


def test_cross_section_skill_extraction(sectioned_priya):
    assert "pgvector" in sectioned_priya.skills
    assert "React" in sectioned_priya.skills
    assert "SQLite" in sectioned_priya.skills


def test_certification_tiering(sectioned_priya):
    assessed = [c for c in sectioned_priya.certifications if c.tier == "assessed"]
    completion = [c for c in sectioned_priya.certifications if c.tier == "completion"]
    assert any("AWS" in c.name for c in assessed)
    assert any("Google" in c.name or "Coursera" in (c.issuer or "") for c in completion)


def test_link_extraction(sectioned_priya):
    assert any(link.link_type == "github" for link in sectioned_priya.links)


def test_no_truncation(sectioned_priya):
    for field in ["summary_text", "skills_text", "projects_text", "experience_text",
                  "education_text", "certifications_text"]:
        text = getattr(sectioned_priya, field)
        if text:
            assert len(model.tokenizer.encode(text)) <= 512


def test_identity_retrieval(make_company):
    temp_company = make_company("Identity Retrieval Test Co")
    resume_id = ingest_resume(temp_company.id, open("tests/Priya_Sharma_Resume_sample.pdf", "rb").read())
    resume = get_resume(temp_company.id, resume_id)

    query_vec = embed_query(resume.skills_text)
    results = search_by_vector(temp_company.id, query_vec, "skills", 5)

    top_resume_id, top_distance = results[0]
    assert str(top_resume_id.resume_id) == resume_id
    assert top_distance < 0.1


@pytest.mark.skip(reason="Only 2 sample resumes exist — needs real volume, revisit in Phase 8's evaluation harness")
def test_embedding_speed_at_scale():
    pass

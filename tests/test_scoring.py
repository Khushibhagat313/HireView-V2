import pytest
from src.retrieval.pipeline import search_and_score
from src.scoring.facets import compute_composite
from src.scoring.cert_relevance import compute_cert_boost
from src.schemas.job import JDRequirements
from src.embedding.embedder import embed_query, embed_documents
from src.config import FACET_WEIGHTS

TEST_COMPANY_ID = "a47c623b-569d-442b-8e0d-ff4c9d8dcf07"


def test_determinism():
    jd_text = open("tests/sample_jd_junior.txt").read()
    results1 = search_and_score(TEST_COMPANY_ID, jd_text)
    results2 = search_and_score(TEST_COMPANY_ID, jd_text)
    assert [r["resume_id"] for r in results1] == [r["resume_id"] for r in results2]


def test_no_empty_results():
    jd_text = open("tests/sample_jd_junior.txt").read()
    results = search_and_score(TEST_COMPANY_ID, jd_text)
    assert len(results) > 0


def test_effective_weights_sum_to_one():
    full_scores = {"skills": 0.5, "projects": 0.5, "experience": 0.5, "achievements_publications": 0.5, "education_certifications": 0.5}
    partial_scores = {"skills": 0.5, "projects": 0.5, "experience": 0.5}
    for scores in (full_scores, partial_scores):
        present_weight_total = sum(FACET_WEIGHTS[f] for f in scores)
        effective_weights = [FACET_WEIGHTS[f] / present_weight_total for f in scores]
        assert abs(sum(effective_weights) - 1.0) < 1e-9


def test_absence_rule_no_penalty():
    with_weak_facet = {"skills": 0.5, "projects": 0.5, "experience": 0.5, "achievements_publications": 0.1, "education_certifications": 0.5}
    without_that_facet = {"skills": 0.5, "projects": 0.5, "experience": 0.5, "education_certifications": 0.5}
    result_with = compute_composite(with_weak_facet)
    result_without = compute_composite(without_that_facet)
    assert result_without["composite_score"] >= result_with["composite_score"]


def test_limited_data_flag():
    assert compute_composite({"skills": 0.5})["limited_data"] is True
    assert compute_composite({"skills": 0.5, "projects": 0.5})["limited_data"] is False


def test_cert_boost_assessed_gate():
    jd = JDRequirements(job_title="Backend Developer", required_skills=["AWS"], hyde_text="x")
    class FakeCert:
        tier = "completion"
        name = "AWS Certified Solutions Architect"
    assert compute_cert_boost(FakeCert(), jd) == 1.0


def test_cert_boost_relevance_gate():
    jd = JDRequirements(job_title="Frontend Developer", required_skills=["React", "CSS"], hyde_text="x")
    class FakeCert:
        tier = "assessed"
        name = "ServSafe Food Handler Certification"
    assert compute_cert_boost(FakeCert(), jd) == 1.0


def test_cert_boost_intended_case():
    jd = JDRequirements(job_title="Cloud Engineer", required_skills=["AWS", "cloud infrastructure"], hyde_text="x")
    class FakeCert:
        tier = "assessed"
        name = "AWS Certified Solutions Architect"
    assert compute_cert_boost(FakeCert(), jd) > 1.0


def test_anti_keyword_stuffing():
    jd_raw_text = open("tests/sample_jd_junior.txt").read()
    query_vec = embed_query("Python, FastAPI, PostgreSQL")
    stuffed_vec = embed_documents([jd_raw_text])[0]
    genuine_vec = embed_documents(["Python, FastAPI, PostgreSQL, SQLAlchemy, Docker, NumPy, Pandas, scikit-learn, Git, Linux, REST APIs"])[0]
    stuffed_similarity = sum(x * y for x, y in zip(query_vec, stuffed_vec))
    genuine_similarity = sum(x * y for x, y in zip(query_vec, genuine_vec))
    assert genuine_similarity > stuffed_similarity
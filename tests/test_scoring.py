import pytest
from types import SimpleNamespace
import numpy as np
from src.retrieval.pipeline import search_and_score, invalidate_search_cache
from src.scoring.facets import compute_composite
from src.scoring.cert_relevance import compute_cert_boost
from src.schemas.job import JDRequirements
from src.embedding.embedder import embed_query, embed_documents
from src.config import FACET_WEIGHTS
from src.scoring.skill_matcher import hybrid_skill_score
from src.scoring.eligibility import check_eligibility
from src.scoring.rerank_blend import blend_rerank_scores

TEST_COMPANY_ID = "a47c623b-569d-442b-8e0d-ff4c9d8dcf07"


def test_determinism():
    jd_text = open("tests/sample_jd_junior.txt").read()
    results1 = search_and_score(TEST_COMPANY_ID, jd_text)
    invalidate_search_cache(TEST_COMPANY_ID)  # force a real second run, not a cache hit
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
    assert result_without["composite_score"] >= result_with["composite_score"] - 1e-9


CORE_FACETS = {"skills": 0.8, "projects": 0.8, "experience": 0.8}


def test_weak_optional_facet_never_lowers_score():
    weak = compute_composite({**CORE_FACETS, "achievements_publications": 0.2})
    assert abs(weak["composite_score"] - compute_composite(CORE_FACETS)["composite_score"]) < 1e-9


def test_strong_optional_facet_raises_score():
    strong = compute_composite({**CORE_FACETS, "achievements_publications": 0.95})
    assert strong["composite_score"] > compute_composite(CORE_FACETS)["composite_score"]


def test_no_required_skills_gives_no_overlap_credit():
    assert abs(hybrid_skill_score(["python"], [], [], 0.7)["hybrid_score"] - 0.7) < 1e-9


def test_overlap_still_counts_when_skills_are_required():
    full = hybrid_skill_score(["python", "sql"], ["python", "sql"], [], 0.7)["hybrid_score"]
    half = hybrid_skill_score(["python"], ["python", "sql"], [], 0.7)["hybrid_score"]
    assert full > half


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


def test_gate_counts_total_years():
    resume = SimpleNamespace(graduation_year=2020)
    jd = SimpleNamespace(eligible_graduation_years=[], min_years_experience=3.0, job_title="Backend Developer")
    assert check_eligibility(resume, jd, [SimpleNamespace(title="Nurse", duration_years=4.0)])
    assert not check_eligibility(resume, jd, [SimpleNamespace(title="Backend Developer", duration_years=2.0)])


def test_blend_weight_zero_changes_nothing():
    results = [{"resume_id": "a", "raw_score": 0.7}, {"resume_id": "b", "raw_score": 0.6}]
    assert blend_rerank_scores(results, {"a": 0.0, "b": 5.0}, 0.0) == results


def test_blend_lets_the_rerank_score_reorder():
    results = [{"resume_id": "a", "raw_score": 0.7}, {"resume_id": "b", "raw_score": 0.6}]
    blended = blend_rerank_scores(results, {"a": 0.0, "b": 5.0}, 1.0)
    assert blended[1]["raw_score"] > blended[0]["raw_score"]


def test_blend_returns_plain_floats():
    results = [{"resume_id": "a", "raw_score": 0.7}, {"resume_id": "b", "raw_score": 0.6}]
    blended = blend_rerank_scores(results, {"a": np.float32(0.0), "b": np.float32(5.0)}, 0.5)
    assert all(type(r["raw_score"]) is float and type(r["display_score"]) is float for r in blended)

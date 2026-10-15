"""API behaviour that needs neither the database nor the LLM: CORS, status codes, response shape, search cache."""
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import src.api.routes.candidates as candidates_route
import src.api.routes.resumes as resumes_route
import src.api.routes.search as search_route
import src.retrieval.pipeline as pipeline
from src.agents.llm_client import AIServiceError
from src.api.main import app

client = TestClient(app)
COMPANY = str(uuid.uuid4())


def _result(candidate_id, resume_id, raw_score):
    return {
        "resume_id": resume_id,
        "candidate_id": candidate_id,
        "candidate_name": "Priya Sharma",
        "raw_score": raw_score,
        "display_score": raw_score * 100,
        "label": "Strong",
        "facet_scores": {"skills": 0.8},
        "limited_data": False,
        "skills": ["fastapi", "python"],
        "matched_required": ["python"],
        "missing_required": ["kubernetes"],
        "matched_preferred": ["fastapi"],
        "work_experience": [SimpleNamespace(title="Backend Intern", duration_years=0.5)],
    }


@pytest.fixture(autouse=True)
def empty_search_cache():
    pipeline._search_cache.clear()
    yield
    pipeline._search_cache.clear()


def test_cors_preflight_allows_frontend_origin_only():
    headers = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    allowed = client.options("/search", headers={"Origin": "http://localhost:5173", **headers})
    blocked = client.options("/search", headers={"Origin": "http://evil.example", **headers})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers


def test_search_response_keeps_skill_fields(monkeypatch):
    monkeypatch.setattr(search_route, "search_and_score", lambda *a, **kw: [_result("c1", "r1", 0.6)])
    body = client.post("/search", json={"company_id": COMPANY, "jd_text": "x"}).json()
    result = body["results"][0]
    assert result["matched_required"] == ["python"]
    assert result["missing_required"] == ["kubernetes"]
    assert result["work_experience"] == [{"title": "Backend Intern", "duration_years": 0.5}]


def test_malformed_uuid_is_422_not_500():
    assert client.get("/candidates/not-a-uuid", params={"company_id": COMPANY}).status_code == 422
    assert client.post("/search", json={"company_id": "abc", "jd_text": "x"}).status_code == 422


def test_unknown_candidate_is_404(monkeypatch):
    monkeypatch.setattr(candidates_route, "get_candidate", lambda *a: None)
    response = client.get(f"/candidates/{uuid.uuid4()}", params={"company_id": COMPANY})
    assert response.status_code == 404


def test_deleting_missing_resume_is_404(monkeypatch):
    monkeypatch.setattr(resumes_route, "delete_resume", lambda *a: False)
    response = client.delete(f"/resumes/{uuid.uuid4()}", params={"company_id": COMPANY})
    assert response.status_code == 404


def test_upload_to_unknown_company_is_404(monkeypatch):
    monkeypatch.setattr(resumes_route, "get_company", lambda *a: None)
    files = {"file": ("cv.pdf", b"%PDF-1.4", "application/pdf")}
    response = client.post("/resumes/upload", data={"company_id": COMPANY}, files=files)
    assert response.status_code == 404


def test_non_pdf_upload_is_422_with_reason(monkeypatch):
    monkeypatch.setattr(resumes_route, "get_company", lambda *a: object())
    files = {"file": ("cv.pdf", b"this is a text file, not a pdf", "application/pdf")}
    response = client.post("/resumes/upload", data={"company_id": COMPANY}, files=files)
    assert response.status_code == 422
    assert "not a readable PDF" in response.json()["detail"]


def test_ai_failure_is_503(monkeypatch):
    def broken(*a, **kw):
        raise AIServiceError("bad JSON twice")
    monkeypatch.setattr(search_route, "search_and_score", broken)
    response = client.post("/search", json={"company_id": COMPANY, "jd_text": "x"})
    assert response.status_code == 503


def test_duplicate_resumes_collapse_to_best_per_candidate():
    results = [_result("c1", "old", 0.40), _result("c1", "new", 0.55), _result("c2", "only", 0.50)]
    best = pipeline.best_resume_per_candidate(results)
    assert sorted((r["candidate_id"], r["resume_id"]) for r in best) == [("c1", "new"), ("c2", "only")]


def test_search_is_cached_until_pool_changes(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "_score_pool", lambda *a: calls.append(a) or [_result("c1", "r1", 0.6)])

    pipeline.search_and_score(COMPANY, "jd")
    pipeline.search_and_score(COMPANY, "jd", max_results=1)  # different filter, same pool
    assert len(calls) == 1

    pipeline.invalidate_search_cache(COMPANY)
    pipeline.search_and_score(COMPANY, "jd")
    assert len(calls) == 2


def test_cached_results_cannot_be_mutated_by_callers(monkeypatch):
    monkeypatch.setattr(pipeline, "_score_pool", lambda *a: [_result("c1", "r1", 0.6)])
    pipeline.search_and_score(COMPANY, "jd")[0]["label"] = "tampered"
    assert pipeline.search_and_score(COMPANY, "jd")[0]["label"] == "Strong"


def test_api_prefix_is_stripped_for_vercel_routing():
    assert client.get("/api/health").json()["status"] == "ok"


def test_access_code_is_enforced_when_configured(monkeypatch):
    import src.api.main as main
    monkeypatch.setattr(main, "ACCESS_CODE", "s3cret")
    monkeypatch.setattr(resumes_route, "list_resumes", lambda *a: [])

    assert client.get("/health").status_code == 200  # open, so the frontend can ask whether a code is needed
    assert client.get("/resumes", params={"company_id": COMPANY}).status_code == 401
    wrong = client.get("/resumes", params={"company_id": COMPANY}, headers={"X-Access-Code": "nope"})
    right = client.get("/api/resumes", params={"company_id": COMPANY}, headers={"X-Access-Code": "s3cret"})
    assert wrong.status_code == 401
    assert right.status_code == 200

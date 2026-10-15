import hashlib
import threading
import time
from collections import OrderedDict
from src.agents.jd_parser import parse_jd
from src.retrieval.query_builder import build_queries
from src.retrieval.searcher import search_candidates
from src.embedding.reranker import rerank
from src.db.store import get_resume, get_work_experiences, get_certifications, get_candidate
from src.ingestion.normalizer import normalize_skills
from src.scoring.eligibility import check_eligibility
from src.scoring.facets import build_facet_queries, get_raw_facet_scores, compute_composite
from src.scoring.skill_matcher import hybrid_skill_score
from src.scoring.cert_relevance import compute_max_cert_boost
from src.scoring.calibration import calibrate_score, label_score, filter_and_rank
from src.config import RERANK_KEEP_TOP_N, SEARCH_CACHE_SIZE, SEARCH_CACHE_TTL_SECONDS
from types import SimpleNamespace

# (company_id, jd_hash, job_posting_id) -> (stored_at, scored pool before threshold/max_results)
_search_cache: OrderedDict[tuple, tuple[float, list[dict]]] = OrderedDict()
_search_cache_lock = threading.Lock()


def search_and_score(company_id: str, jd_text: str, job_posting_id: str = None, threshold: float = None, max_results: int = None) -> list[dict]:
    key = (company_id, hashlib.sha256(jd_text.encode()).hexdigest(), job_posting_id)

    with _search_cache_lock:
        cached = _search_cache.get(key)
        if cached and time.monotonic() - cached[0] < SEARCH_CACHE_TTL_SECONDS:
            _search_cache.move_to_end(key)
            scored = cached[1]
        else:
            scored = None

    if scored is None:
        scored = _score_pool(company_id, jd_text, job_posting_id)
        with _search_cache_lock:
            _search_cache[key] = (time.monotonic(), scored)
            _search_cache.move_to_end(key)
            while len(_search_cache) > SEARCH_CACHE_SIZE:
                _search_cache.popitem(last=False)

    # copies, so callers can't alter what's cached
    return filter_and_rank([dict(r) for r in scored], threshold=threshold, max_results=max_results)


def invalidate_search_cache(company_id: str) -> None:
    """Call whenever a company's resume pool changes (upload, delete)."""
    with _search_cache_lock:
        for key in [k for k in _search_cache if k[0] == company_id]:
            del _search_cache[key]


def best_resume_per_candidate(results: list[dict]) -> list[dict]:
    best = {}
    for r in results:
        current = best.get(r["candidate_id"])
        if current is None or r["raw_score"] > current["raw_score"]:
            best[r["candidate_id"]] = r
    return list(best.values())


def _score_pool(company_id: str, jd_text: str, job_posting_id: str = None) -> list[dict]:
    jd = parse_jd(jd_text)
    queries = build_queries(jd)
    resume_ids = search_candidates(company_id, queries, job_posting_id=job_posting_id)

    reranked = rerank(company_id, jd.hyde_text, resume_ids)
    top_candidates = reranked[:RERANK_KEEP_TOP_N]

    facet_queries = build_facet_queries(jd)

    results = []
    for resume_id, rerank_score in top_candidates:
        resume = get_resume(company_id, str(resume_id))
        work_experience = get_work_experiences(company_id, str(resume_id))
        work_experience = [SimpleNamespace(title=w.title, duration_years=w.duration_years) for w in work_experience]
        certifications = get_certifications(company_id, str(resume_id))

        if not check_eligibility(resume, jd, work_experience):
            continue

        facet_scores = get_raw_facet_scores(company_id, str(resume_id), facet_queries)

        hybrid = None
        if "skills" in facet_scores:
            hybrid = hybrid_skill_score(resume.skills or [], jd.required_skills, jd.preferred_skills, facet_scores["skills"])
            cert_boost = compute_max_cert_boost(certifications, jd)
            facet_scores["skills"] = hybrid["hybrid_score"] * cert_boost

        scored = compute_composite(facet_scores)

        results.append({
            "resume_id": str(resume_id),
            "candidate_id": str(resume.candidate_id),
            "candidate_name": get_candidate(company_id, str(resume.candidate_id)).name,
            "raw_score": scored["composite_score"],
            "display_score": calibrate_score(scored["composite_score"]),
            "label": label_score(scored["composite_score"]),
            "facet_scores": scored["facet_scores"],
            "limited_data": scored["limited_data"],
            "skills": sorted(normalize_skills(resume.skills or [])),
            "matched_required": hybrid["matched_required"] if hybrid else [],
            "missing_required": hybrid["missing_required"] if hybrid else [],
            "matched_preferred": hybrid["matched_preferred"] if hybrid else [],
            "work_experience": work_experience,
        })

    return best_resume_per_candidate(results)

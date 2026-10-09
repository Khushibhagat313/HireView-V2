from types import SimpleNamespace

from src.agents.jd_parser import parse_jd
from src.retrieval.query_builder import build_queries
from src.retrieval.searcher import search_candidates
from src.embedding.reranker import rerank
from src.db.store import get_resumes, get_work_experiences_many, get_certifications_many, get_candidates
from src.ingestion.normalizer import normalize_skills
from src.scoring.eligibility import check_eligibility
from src.scoring.facets import build_facet_queries, get_raw_facet_scores, compute_composite
from src.scoring.skill_matcher import hybrid_skill_score
from src.scoring.cert_relevance import compute_max_cert_boost
from src.scoring.calibration import calibrate_score, label_score, filter_and_rank
from src.config import RERANK_KEEP_TOP_N, RERANK_BLEND_WEIGHT
from src.scoring.rerank_blend import blend_rerank_scores


def search_and_score(
    company_id: str,
    jd_text: str,
    job_posting_id: str = None,
    threshold: float = None,
    max_results: int = None,
) -> list[dict]:
    jd = parse_jd(jd_text)
    queries = build_queries(jd)
    resume_ids = search_candidates(company_id, queries, job_posting_id=job_posting_id)

    reranked = rerank(company_id, jd.hyde_text, resume_ids)
    rerank_scores = {str(resume_id): score for resume_id, score in reranked}
    kept_ids = [str(resume_id) for resume_id, _ in reranked[:RERANK_KEEP_TOP_N]]

    resumes = get_resumes(company_id, kept_ids)
    work_experiences = get_work_experiences_many(company_id, kept_ids)
    certifications_by_resume = get_certifications_many(company_id, kept_ids)

    eligible = []
    for resume_id in kept_ids:
        resume = resumes[resume_id]
        work_experience = [
            SimpleNamespace(title=w.title, duration_years=w.duration_years)
            for w in work_experiences[resume_id]
        ]
        if check_eligibility(resume, jd, work_experience):
            eligible.append((resume_id, resume, work_experience))

    candidates = get_candidates(company_id, [str(resume.candidate_id) for _, resume, _ in eligible])
    facet_queries = build_facet_queries(jd)

    results = []
    for resume_id, resume, work_experience in eligible:
        facet_scores = get_raw_facet_scores(company_id, resume_id, facet_queries)

        hybrid = None
        if "skills" in facet_scores:
            hybrid = hybrid_skill_score(
                resume.skills or [],
                jd.required_skills,
                jd.preferred_skills,
                facet_scores["skills"],
            )
            cert_boost = compute_max_cert_boost(certifications_by_resume[resume_id], jd)
            facet_scores["skills"] = hybrid["hybrid_score"] * cert_boost

        scored = compute_composite(facet_scores)

        results.append({
            "resume_id": resume_id,
            "candidate_id": str(resume.candidate_id),
            "candidate_name": candidates[str(resume.candidate_id)].name,
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

    results = blend_rerank_scores(results, rerank_scores, RERANK_BLEND_WEIGHT)
    return filter_and_rank(results, threshold=threshold, max_results=max_results)
from src.agents.jd_parser import parse_jd
from src.retrieval.query_builder import build_queries
from src.retrieval.searcher import search_candidates
from src.embedding.reranker import rerank
from src.db.store import get_resume, get_work_experiences, get_certifications, get_candidate
from src.scoring.eligibility import check_eligibility
from src.scoring.facets import build_facet_queries, get_raw_facet_scores, compute_composite
from src.scoring.skill_matcher import hybrid_skill_score
from src.scoring.cert_relevance import compute_max_cert_boost
from src.scoring.calibration import calibrate_score, label_score, filter_and_rank
from src.config import RERANK_KEEP_TOP_N

def search_and_score(company_id: str, jd_text: str, job_posting_id: str = None, threshold: float = None, max_results: int = None) -> list[dict]:
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
        certifications = get_certifications(company_id, str(resume_id))

        if not check_eligibility(resume, jd, work_experience):
            continue

        facet_scores = get_raw_facet_scores(company_id, str(resume_id), facet_queries)

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
        })

    return filter_and_rank(results, threshold=threshold, max_results=max_results)
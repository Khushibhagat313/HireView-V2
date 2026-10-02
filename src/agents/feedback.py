from src.agents.llm_client import call_llm
from src.schemas.job import JDRequirements

FACET_NAMES = {
    "skills": "skills",
    "projects": "projects",
    "experience": "work experience",
    "achievements_publications": "achievements and publications",
    "education_certifications": "education and certifications",
}

FEEDBACK_PROMPT = """You are explaining to a recruiter why a candidate received the match label below for a job. The label and the skill matches were computed by a deterministic system. Your job is only to explain them. Never re-score, adjust, or dispute them.

Job: {job_title}
Required skills: {required_skills}
Preferred skills: {preferred_skills}

Match label: {label}
Required skills the candidate has: {matched_required}
Required skills the candidate is missing: {missing_required}
Preferred skills the candidate has: {matched_preferred}
Work experience: {experience}
Strongest areas of the profile: {strongest}
{limited_note}
Rules:
- Start with the label, for example "This is {article} {label} match because ...". Do not state any score or percentage.
- Mention only skills and experience listed above. Never invent skills, employers, or achievements.
- Refer to the person only as "the candidate" or with "they" and "their". Never use he, she, his, or her, and never comment on or guess their name, gender, age, nationality, ethnicity, or graduation year.
- Write 3 to 5 sentences of plain prose, with no bullet points or headings.
- Describe work experience only by role title and duration. Do not say what the work involved."""


_feedback_cache: dict[str, str] = {}


def _join(items: list[str]) -> str:
    return ", ".join(items) if items else "none"


def _describe_experience(work_experience: list) -> str:
    if not work_experience:
        return "none listed"
    return "; ".join(f"{w.title} ({w.duration_years} years)" for w in work_experience)


def _strongest_areas(facet_scores: dict) -> str:
    ranked = sorted(facet_scores, key=facet_scores.get, reverse=True)[:2]
    return ", ".join(FACET_NAMES.get(k, k) for k in ranked) or "not available"


def generate_feedback(company_id: str, jd_hash: str, jd: JDRequirements, candidate: dict) -> str:
    cache_key = f"{company_id}:{candidate['resume_id']}:{jd_hash}"
    if cache_key in _feedback_cache:
        return _feedback_cache[cache_key]

    limited_note = (
        "Note: the resume had very little information, so say this ranking rests on limited data.\n"
        if candidate["limited_data"]
        else ""
    )
    prompt = FEEDBACK_PROMPT.format(
        job_title=jd.job_title,
        required_skills=_join(jd.required_skills),
        preferred_skills=_join(jd.preferred_skills),
        label=candidate["label"],
        article="an" if candidate["label"][0] in "AEIOU" else "a",
        matched_required=_join(candidate["matched_required"]),
        missing_required=_join(candidate["missing_required"]),
        matched_preferred=_join(candidate["matched_preferred"]),
        experience=_describe_experience(candidate["work_experience"]),
        strongest=_strongest_areas(candidate["facet_scores"]),
        limited_note=limited_note,
    )

    feedback = call_llm(prompt).strip()
    _feedback_cache[cache_key] = feedback
    return feedback
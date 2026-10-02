import re
from collections import Counter

from src.agents.conversation.state import HiringState
from src.config import HIDDEN_GEM_FACET_THRESHOLD, HIDDEN_GEM_RANK_CUTOFF
from src.ingestion.normalizer import normalize_skills
from src.scoring.eligibility import compute_field_specific_experience
from groq import APIError
from src.agents.feedback import generate_feedback
from src.agents.interview_guide import GuideUnavailable, generate_interview_guide
from src.agents.llm_client import call_llm

COMPARE_PROMPT = """You are helping a recruiter compare two candidates for a job. The labels, skill matches, and ranking below were computed by a deterministic system. Your job is only to explain how the candidates differ. Never re-score, adjust, or dispute them.

Job: {job_title}
Required skills: {required_skills}
Preferred skills: {preferred_skills}

The system ranked Candidate A above Candidate B.

Candidate A
{profile_a}

Candidate B
{profile_b}

Rules:
- Compare the two against the job's requirements: where each is stronger, where each has gaps, and what separates them. Explain why Candidate A is ranked higher using only the information above.
- Always write "Candidate A" or "Candidate B" exactly like that. Never use pronouns, and never comment on or guess names, gender, age, nationality, ethnicity, or graduation year.
- Mention only skills and experience listed above. Never invent skills, employers, or achievements.
- Write 4 to 6 sentences of plain prose, with no bullet points or headings.
- Do not mention how the labels or ranking were computed, and do not use the words "system" or "deterministic"."""

GENERAL_PROMPT = """You are an assistant helping a recruiter review candidates for a job. The labels, skill matches, and ranking below are final. Answer the recruiter's question using only the information below. Never re-score, adjust, or dispute the labels or ranking.

Job: {job_title}
Required skills: {required_skills}
Preferred skills: {preferred_skills}

Pool summary (exact counts):
{pool_summary}

Candidates, from highest to lowest rank:
{candidate_lines}

Recruiter's question: {question}

Rules:
- For any question about how many or how often, use the pool summary. Do not count yourself.
- Refer to candidates only as "Candidate 1", "Candidate 2", and so on, exactly as listed, writing "Candidate N" each time even when naming several. Never use pronouns, and never comment on or guess names, gender, age, nationality, ethnicity, or graduation year.
- If the question cannot be answered from the information above, say what is missing instead of guessing.
- Mention only skills and experience listed above. Never invent skills, employers, or achievements.
- Do not mention how the labels or ranking were computed, and do not use the words "system" or "deterministic".
- Keep the answer to a short paragraph of plain prose, or a short list if the question asks about several candidates."""

def show_top_n(state: HiringState) -> dict:
    match = re.search(r"\btop\s+(\d+)\b", state["query"], re.IGNORECASE)
    n = int(match.group(1)) if match else 5
    return {"response_candidates": state["candidates"][:n]}


def filter_by_skill(state: HiringState) -> dict:
    match = re.search(
        r"(?:who (?:knows|has)|skilled in|filter by skill:?)\s+(.+)",
        state["query"],
        re.IGNORECASE,
    )
    if not match:
        return {"response_candidates": []}

    raw_skill = match.group(1).strip().strip(".?!")
    skill = next(iter(normalize_skills([raw_skill])), raw_skill.lower())
    matches = [c for c in state["candidates"] if skill in c.get("skills", [])]
    return {"response_candidates": matches}


def hidden_gems(state: HiringState) -> dict:
    ranked = state["candidates"]
    gems = [
        c for c in ranked[HIDDEN_GEM_RANK_CUTOFF:]
        if c.get("facet_scores", {}).get("skills", 0) >= HIDDEN_GEM_FACET_THRESHOLD
        or c.get("facet_scores", {}).get("projects", 0) >= HIDDEN_GEM_FACET_THRESHOLD
    ]
    return {"response_candidates": gems}


def parse_experience_query(query: str) -> tuple[float, str] | None:
    years_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*years?", query, re.IGNORECASE)
    title_match = re.search(r"\bas\s+(?:an?\s+)?(.+)", query, re.IGNORECASE)

    if not years_match or not title_match:
        return None

    min_years = float(years_match.group(1))
    title = title_match.group(1).strip().strip(".?!")
    return min_years, title


def filter_by_experience(state: HiringState) -> dict:
    parsed = parse_experience_query(state["query"])
    if parsed is None:
        return {"response_candidates": []}

    min_years, title = parsed
    matches = [
        c for c in state["candidates"]
        if compute_field_specific_experience(title, c.get("work_experience", [])) >= min_years
    ]
    return {"response_candidates": matches}


def _first_per_candidate(matches: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for c in matches:
        if c["candidate_id"] not in seen:
            seen.add(c["candidate_id"])
            unique.append(c)
    return unique


def find_candidates_in_query(query: str, candidates: list[dict]) -> list[dict]:
    query_lower = query.lower()
    query_tokens = set(re.findall(r"\w+", query_lower))

    named = [(c, (c["candidate_name"] or "").lower()) for c in candidates]
    full_matches = [
        c for c, name in named
        if name and re.search(rf"\b{re.escape(name)}\b", query_lower)
    ]
    if full_matches:
        return _first_per_candidate(full_matches)

    return _first_per_candidate([
        c for c, name in named
        if {t for t in re.findall(r"\w+", name) if len(t) >= 3} & query_tokens
    ])


def _resolve_single_candidate(state: HiringState) -> tuple[dict | None, dict | None]:
    matches = find_candidates_in_query(state["query"], state["candidates"])
    if not matches:
        return None, {"response_text": "I couldn't tell which candidate you mean. Please include a name from the results."}
    if len(matches) > 1:
        names = ", ".join(c["candidate_name"] for c in matches)
        return None, {"response_text": f"More than one candidate matches: {names}. Please use a full name."}
    return matches[0], None


def explain_score(state: HiringState) -> dict:
    candidate, problem = _resolve_single_candidate(state)
    if problem:
        return problem

    try:
        feedback = generate_feedback(state["company_id"], state["jd_hash"], state["jd"], candidate)
    except APIError as e:
        return {
            "response_text": "I couldn't generate that explanation right now. Please try again.",
            "errors": state["errors"] + [f"explain_score: {e}"],
        }
    return {"response_text": feedback}


def interview_questions(state: HiringState) -> dict:
    candidate, problem = _resolve_single_candidate(state)
    if problem:
        return problem

    try:
        guide = generate_interview_guide(state["company_id"], state["jd_hash"], state["jd"], candidate)
    except (APIError, GuideUnavailable) as e:
        return {
            "response_text": "I couldn't generate the interview questions right now. Please try again.",
            "errors": state["errors"] + [f"interview_questions: {e}"],
        }
    return {"response_text": guide}

def _profile(candidate: dict) -> str:
    roles = "; ".join(f"{w.title} ({w.duration_years} years)" for w in candidate["work_experience"])
    return "\n".join([
        f"Match label: {candidate['label']}",
        f"Required skills held: {', '.join(candidate['matched_required']) or 'none'}",
        f"Required skills missing: {', '.join(candidate['missing_required']) or 'none'}",
        f"Preferred skills held: {', '.join(candidate['matched_preferred']) or 'none'}",
        f"Work experience: {roles or 'none listed'}",
    ])


def compare(state: HiringState) -> dict:
    matches = find_candidates_in_query(state["query"], state["candidates"])
    if len(matches) != 2:
        return {"response_text": "Please name exactly two candidates from the results to compare."}

    higher, lower = matches
    jd = state["jd"]
    prompt = COMPARE_PROMPT.format(
        job_title=jd.job_title,
        required_skills=", ".join(jd.required_skills) or "none",
        preferred_skills=", ".join(jd.preferred_skills) or "none",
        profile_a=_profile(higher),
        profile_b=_profile(lower),
    )

    try:
        comparison = call_llm(prompt).strip()
    except APIError as e:
        return {
            "response_text": "I couldn't generate that comparison right now. Please try again.",
            "errors": state["errors"] + [f"compare: {e}"],
        }

    comparison = re.sub(r"Candidate\s+A\b", lambda m: higher["candidate_name"], comparison)
    comparison = re.sub(r"Candidate\s+B\b", lambda m: lower["candidate_name"], comparison)
    return {"response_text": comparison}

def _summary_line(index: int, candidate: dict) -> str:
    roles = "; ".join(f"{w.title} ({w.duration_years} years)" for w in candidate["work_experience"])
    return (
        f"Candidate {index}: {candidate['label']} match. "
        f"Required skills held: {', '.join(candidate['matched_required']) or 'none'}. "
        f"Required skills missing: {', '.join(candidate['missing_required']) or 'none'}. "
        f"All listed skills: {', '.join(candidate['skills']) or 'none'}. "
        f"Roles: {roles or 'none listed'}."
    )


def _label_names(question: str, candidates: list[dict]) -> str:
    names = [(c["candidate_name"] or "").strip() for c in candidates]
    owners: dict[str, int] = {}
    for name in names:
        for token in {t for t in re.findall(r"\w+", name.lower()) if len(t) >= 3}:
            owners[token] = owners.get(token, 0) + 1

    for index, name in enumerate(names, start=1):
        if not name:
            continue
        unique = [t for t in re.findall(r"\w+", name) if len(t) >= 3 and owners[t.lower()] == 1]
        for term in [name, *unique]:
            question = re.sub(rf"\b{re.escape(term)}\b", f"Candidate {index}", question, flags=re.IGNORECASE)
    return question


def _pool_summary(candidates: list[dict]) -> str:
    total = len(candidates)
    labels = Counter(c["label"] for c in candidates)
    required = {s for c in candidates for s in c["matched_required"] + c["missing_required"]}
    held_preferred = {s for c in candidates for s in c.get("matched_preferred", [])}

    missing = sorted(
        ((sum(s in c["missing_required"] for c in candidates), s) for s in required),
        key=lambda item: (-item[0], item[1]),
    )
    missing_text = ", ".join(f"{s} (missing for {n} of {total})" for n, s in missing) or "none"
    preferred_text = ", ".join(
        f"{s} (held by {sum(s in c.get('matched_preferred', []) for c in candidates)} of {total})"
        for s in sorted(held_preferred)
    ) or "none"

    return "\n".join([
        f"{total} candidates in total.",
        "Match labels: " + ", ".join(f"{label} {n}" for label, n in labels.most_common()) + ".",
        f"Required skills, most often missing first: {missing_text}.",
        f"Preferred skills held: {preferred_text}.",
    ])


def general(state: HiringState) -> dict:
    jd = state["jd"]
    candidates = _first_per_candidate(state["candidates"])
    lines = "\n".join(_summary_line(i, c) for i, c in enumerate(candidates, start=1))
    prompt = GENERAL_PROMPT.format(
        job_title=jd.job_title,
        required_skills=", ".join(jd.required_skills) or "none",
        preferred_skills=", ".join(jd.preferred_skills) or "none",
        pool_summary=_pool_summary(candidates),
        candidate_lines=lines or "No candidates were found.",
        question=_label_names(state["query"], candidates),
    )

    try:
        answer = call_llm(prompt).strip()
    except APIError as e:
        return {
            "response_text": "I couldn't answer that right now. Please try again.",
            "errors": state["errors"] + [f"general: {e}"],
        }

    names = {i: c["candidate_name"] for i, c in enumerate(candidates, start=1)}
    answer = re.sub(r"Candidate\s+(\d+)", lambda m: names.get(int(m.group(1))) or m.group(0), answer)
    return {"response_text": answer}

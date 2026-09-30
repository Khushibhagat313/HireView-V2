import re

from src.agents.conversation.state import HiringState
from src.config import HIDDEN_GEM_FACET_THRESHOLD, HIDDEN_GEM_RANK_CUTOFF
from src.ingestion.normalizer import normalize_skills



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
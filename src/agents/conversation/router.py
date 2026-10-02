import re

from src.agents.conversation.state import HiringState

KEYWORD_PATTERNS: dict[str, re.Pattern] = {
    "show_top_n": re.compile(r"\btop\s+\d+\b", re.IGNORECASE),
    "hidden_gems": re.compile(r"\bhidden gems?\b|\bunderrated\b|\boverlooked\b", re.IGNORECASE),
    "filter_by_experience": re.compile(r"\d+\+?\s*years?.*\bas\b|\bfilter by experience\b", re.IGNORECASE),
    "filter_by_skill": re.compile(r"\bwho (knows|has)\b|\bskilled in\b|\bfilter by skill\b", re.IGNORECASE),
    "explain_score": re.compile(r"\bwhy\b.*\b(score|ranked|rank)\b|\bexplain\b.*\bscore\b", re.IGNORECASE),
    "compare": re.compile(r"\bcompare\b|\bvs\.?\b|\bversus\b", re.IGNORECASE),
    "interview_questions": re.compile(r"\binterview questions?\b|\binterview guide\b", re.IGNORECASE),
}


def match_by_keyword(query: str) -> str | None:
    for intent, pattern in KEYWORD_PATTERNS.items():
        if pattern.search(query):
            return intent
    return None


def classify_intent(state: HiringState) -> dict:
    intent = match_by_keyword(state["query"])
    if intent is not None:
        return {"intent": intent}

    return {"intent": "general"}




import re

SOLO = re.compile(r"self[- ]?employed|freelanc|independent", re.IGNORECASE)
INTERN = re.compile(r"\bintern(ship)?\b|trainee|apprentice", re.IGNORECASE)
SOLO_WEIGHT = 0.5
INTERN_WEIGHT = 0.5
FULL_CREDIT_MULTIPLE = 2.0


def entry_weight(entry: dict) -> float:
    text = f"{entry['title']} {entry['company']}"
    if SOLO.search(text):
        return SOLO_WEIGHT
    if INTERN.search(text):
        return INTERN_WEIGHT
    return 1.0


def tenure_score(entries: list[dict], min_years: float | None, by_type: bool) -> float | None:
    if not min_years or not entries:
        return None
    years = sum(e["duration_years"] * (entry_weight(e) if by_type else 1.0) for e in entries)
    return min(1.0, years / (FULL_CREDIT_MULTIPLE * min_years))

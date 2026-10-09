import json
from collections import defaultdict
from pathlib import Path

from eval.reading import entry_weight, tenure_score

resumes = {r["candidate_id"]: r for r in json.loads(Path("eval/data/resumes.json").read_text(encoding="utf-8"))}
lines = Path("eval/queries.jsonl").read_text(encoding="utf-8").splitlines()
queries = [json.loads(line) for line in lines if line.strip()]
flagged = {c for c, r in resumes.items() if any(entry_weight(e) < 1 for e in r["work_experience"])}

stats = defaultdict(lambda: {"n": 0, "flagged": 0, "plain": 0.0, "typed": 0.0})
for q in queries:
    for cand, grade in q["ground_truth"].items():
        entries = resumes[cand]["work_experience"]
        plain = tenure_score(entries, q["min_years_experience"], False)
        if plain is None:
            continue
        s = stats[grade]
        s["n"] += 1
        s["flagged"] += cand in flagged
        s["plain"] += plain
        s["typed"] += tenure_score(entries, q["min_years_experience"], True)

for grade in (3, 2, 1, 0):
    s = stats[grade]
    if s["n"]:
        print(
            "grade",
            grade,
            "|",
            s["n"],
            "graded pairs |",
            s["flagged"],
            "flagged | tenure any",
            round(s["plain"] / s["n"], 2),
            "| tenure by type",
            round(s["typed"] / s["n"], 2),
        )

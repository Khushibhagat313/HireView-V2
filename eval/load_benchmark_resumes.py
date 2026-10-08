import argparse
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from src.db.store import create_company
from src.ingestion.pipeline import store_sectioned_resume

EVAL_DIR = Path(__file__).parent
RESUMES_PATH = EVAL_DIR / "data" / "resumes.json"
QUERIES_PATH = EVAL_DIR / "queries.jsonl"
MAP_PATH = EVAL_DIR / "data" / "cand_id_map.json"

RESUME_KEYS = {
    "candidate_id", "candidate_name", "graduation_year", "skills", "work_experience", "certifications",
    "summary_text", "projects_text", "experience_text", "achievements_text", "publications_text",
}
CERT_KEYS = {"name", "tier"}    
WORK_KEYS = {"title", "company", "duration_years"}
TIERS = {"assessed", "completion"}


def load_resumes() -> list[dict]:
    return json.loads(RESUMES_PATH.read_text(encoding="utf-8"))


def load_queries() -> list[dict]:
    lines = QUERIES_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def validate(resumes: list[dict], queries: list[dict]) -> list[str]:
    problems = []
    ids = [r.get("candidate_id") for r in resumes]
    if len(set(ids)) != len(ids):
        problems.append("duplicate candidate_id values")

    for r in resumes:
        cid = r.get("candidate_id")
        missing = RESUME_KEYS - set(r)
        if missing:
            problems.append(f"{cid}: missing keys {sorted(missing)}")
            continue
        for cert in r["certifications"]:
            if not CERT_KEYS <= set(cert) or cert["tier"] not in TIERS:
                problems.append(f"{cid}: bad certification {cert}")
        for entry in r["work_experience"]:
            if not WORK_KEYS <= set(entry):
                problems.append(f"{cid}: bad work_experience entry {entry}")

    known = set(ids)
    for q in queries:
        qid = q.get("query_id")
        grades = q.get("ground_truth", {})
        if set(grades) - known:
            problems.append(f"{qid}: ground_truth names unknown candidates {sorted(set(grades) - known)}")
        if not set(grades.values()) <= {0, 1, 2, 3}:
            problems.append(f"{qid}: grades outside 0-3")
        if 3 not in grades.values():
            problems.append(f"{qid}: no grade-3 candidate")
    return problems


def summarize(resumes: list[dict], queries: list[dict]) -> None:
    tiers = Counter(c.get("tier") for r in resumes for c in r.get("certifications", []))
    difficulties = Counter(q.get("difficulty") for q in queries)
    print(f"resumes: {len(resumes)} | queries: {len(queries)} {dict(difficulties)}")
    print(f"certifications by tier: {dict(tiers)}")
    print(
        f"achievements present: {sum(bool(r.get('achievements_text')) for r in resumes)}"
        f" | publications present: {sum(bool(r.get('publications_text')) for r in resumes)}"
    )


def _cert_label(cert: dict) -> str:
    issuer = cert.get("issuer", "")
    return f"{cert['name']} ({issuer})" if issuer else cert["name"]


def to_sectioned(record: dict) -> SimpleNamespace:
    certs = record["certifications"]
    return SimpleNamespace(
        candidate_name=record["candidate_name"],
        candidate_email=f"{record['candidate_id']}@benchmark.test",
        candidate_phone=None,
        summary_text=record["summary_text"],
        skills=record["skills"],
        skills_text=", ".join(record["skills"]),
        projects_text=record["projects_text"],
        experience_text=record["experience_text"],
        achievements_text=record["achievements_text"],
        publications_text=record["publications_text"],
        education_text="",
        certifications_text="; ".join(_cert_label(c) for c in certs),
        years_experience=min(sum(w["duration_years"] for w in record["work_experience"]), 40.0),
        graduation_year=record["graduation_year"],
        certifications=[SimpleNamespace(name=c["name"], issuer=c.get("issuer", ""), tier=c["tier"]) for c in certs],
        links=[],
        work_experience=[
            SimpleNamespace(title=w["title"], company_name=w["company"], duration_years=w["duration_years"])
            for w in record["work_experience"]
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="validate the data files without touching the database")
    parser.add_argument("--force", action="store_true", help="load even if cand_id_map.json already exists")
    args = parser.parse_args()

    resumes = load_resumes()
    queries = load_queries()
    summarize(resumes, queries)

    problems = validate(resumes, queries)
    for problem in problems:
        print("PROBLEM:", problem)
    if problems:
        raise SystemExit(f"{len(problems)} problem(s) found; nothing was loaded")
    if args.dry_run:
        print("dry run OK")
        return

    if MAP_PATH.exists() and not args.force:
        raise SystemExit(f"{MAP_PATH.name} already exists; delete it or pass --force")

    company_id = str(create_company("hireview-eval-benchmark").id)
    print("created benchmark company", company_id)

    id_map = {}
    try:
        for i, record in enumerate(resumes, start=1):
            id_map[record["candidate_id"]] = store_sectioned_resume(company_id, to_sectioned(record))
            print(f"[{i}/{len(resumes)}] {record['candidate_id']} loaded")
    except Exception:
        print(f"load failed after {len(id_map)} resumes; company {company_id} is partially loaded, delete it before retrying")
        raise

    MAP_PATH.write_text(json.dumps({"company_id": company_id, "resumes": id_map}, indent=2), encoding="utf-8")
    print("saved", MAP_PATH)


if __name__ == "__main__":
    main()
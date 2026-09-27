import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from src.retrieval.pipeline import search_and_score
from src.db.store import get_candidate

def main():
    parser = argparse.ArgumentParser(description="Search resumes against a job description")
    parser.add_argument("company_id", help="Company UUID to search within")
    parser.add_argument("--jd", required=True, help="Path to a job description text file")
    parser.add_argument("--top", type=int, default=10, help="Number of results to show")
    parser.add_argument("--job-posting-id", default=None, help="Restrict search to this job posting's applicants")
    parser.add_argument("--threshold", type=float, default=None, help="Minimum display score to show")
    args = parser.parse_args()

    jd_text = Path(args.jd).read_text()
    results = search_and_score(args.company_id, jd_text, job_posting_id=args.job_posting_id, threshold=args.threshold, max_results=args.top)

    if not results:
        print("No candidates matched.")
        return

    for i, r in enumerate(results, 1):
        candidate = get_candidate(args.company_id, r["candidate_id"])
        print(f"{i}. {candidate.name} — {r['display_score']:.1f} ({r['label']})")
        for facet, score in r["facet_scores"].items():
            print(f"     {facet}: {score:.3f}")
        if r["limited_data"]:
            print("     limited resume data")

if __name__ == "__main__":
    main()
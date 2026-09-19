import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from src.ingestion.pipeline import ingest_resume

def main():
    parser = argparse.ArgumentParser(description="Ingest all PDF resumes in a folder")
    parser.add_argument("company_id", help="Company UUID to ingest resumes under")
    parser.add_argument("folder", help="Folder containing resume PDFs")
    args = parser.parse_args()

    folder = Path(args.folder)
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {folder}")
        return

    succeeded = 0
    failed = 0
    for pdf_path in pdf_files:
        print(f"Ingesting {pdf_path.name}...", end=" ")
        try:
            resume_id = ingest_resume(args.company_id, pdf_path.read_bytes())
            print(f"OK -> {resume_id}")
            succeeded += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    print(f"\nDone. {succeeded} succeeded, {failed} failed.")

if __name__ == "__main__":
    main()
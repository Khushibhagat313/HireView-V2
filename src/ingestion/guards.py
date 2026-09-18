import pymupdf
from src.config import MAX_FILE_SIZE_MB, MAX_PAGES,  MIN_EXTRACTED_CHARS
from src.ingestion.extractor import extract_text

def check_size(pdf_bytes: bytes) -> None:
    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(f"PDF is {size_mb:.1f}MB, exceeds the {MAX_FILE_SIZE_MB}MB limit")



def check_pages(pdf_bytes: bytes) -> None:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    if len(doc) > MAX_PAGES:
        raise ValueError(f"PDF has {len(doc)} pages, exceeds the {MAX_PAGES} page limit")


def is_scanned(pdf_bytes: bytes) -> None:
    text = extract_text(pdf_bytes)
    if len(text.strip()) < MIN_EXTRACTED_CHARS:
        raise ValueError(f"Extracted only {len(text.strip())} characters — likely a scanned image with no real text layer")        



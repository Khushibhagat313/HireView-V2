# src/ingestion/extractor.py
import pymupdf
from src.config import COLUMN_GAP_THRESHOLD

def extract_text(pdf_bytes: bytes) -> str:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    lines = []
    for page in doc:
        blocks = page.get_text("blocks")
        boundary = _find_column_boundary(blocks, page.rect.width)
        blocks.sort(key=lambda b: (b[0] >= boundary, b[1], b[0]))
        lines.extend(b[4] for b in blocks)
    return "\n".join(lines)


def _find_column_boundary(blocks, page_width):
    x0s = sorted(set(round(b[0]) for b in blocks))
    if len(x0s) < 2:
        return page_width
    gap, boundary = max((x0s[i + 1] - x0s[i], (x0s[i] + x0s[i + 1]) / 2) for i in range(len(x0s) - 1))
    if gap < page_width * COLUMN_GAP_THRESHOLD:
        return page_width
    return boundary
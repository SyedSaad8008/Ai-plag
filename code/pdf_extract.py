"""
PDF extraction (PDF is INPUT-ONLY in this product — docs/06) — reference.

PyMuPDF gives text + block bboxes (bboxes power "highlight on page" in the UI).
Scanned PDFs (no text layer) are flagged for OCR instead of failing.

Requires: pip install pymupdf
Adapt into bi-plagiarism/backend/ingest/pdf_reader.py.
"""
from __future__ import annotations


def extract(path: str) -> dict:
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    pages, full_text = [], []
    for pno, page in enumerate(doc):
        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, type)
        pb = [
            {"bbox": [round(v, 1) for v in b[:4]], "text": b[4].strip()}
            for b in blocks
            if b[6] == 0 and b[4].strip()
        ]
        page_text = "\n".join(b["text"] for b in pb)
        pages.append({"page": pno + 1, "blocks": pb, "chars": len(page_text)})
        full_text.append(page_text)
    meta = doc.metadata or {}
    doc.close()
    text = "\n\n".join(full_text)
    return {
        "text": text,
        "pages": pages,
        "chars": len(text),
        "needs_ocr": len(text) < 50 * max(1, len(pages)),  # <50 chars/page => scanned
        "title": meta.get("title") or "",
    }


def find_snippet_pages(pages: list[dict], needle: str) -> list[int]:
    """Which pages contain this matched text (for the report's source preview)."""
    hits = []
    for p in pages:
        joined = "\n".join(b["text"] for b in p["blocks"]).lower()
        if needle.lower() in joined:
            hits.append(p["page"])
    return hits


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        info = extract(sys.argv[1])
        print(f"pages={len(info['pages'])} chars={info['chars']} needs_ocr={info['needs_ocr']}")
        print(info["text"][:400])
    else:
        print("usage: python pdf_extract.py file.pdf")
        print("self-test skipped (needs a PDF); wire a generated-PDF test in pytest")

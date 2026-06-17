"""
app/ingestion/pdf_extractor.py
────────────────────────────────
Extracts text + tables from PDFs.
  - PyMuPDF  → raw text extraction (fast, handles most PDFs)
  - pdfplumber → structured table extraction → markdown

Returns a list of {text, page, type} dicts.
"""

import io
import hashlib
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
import pdfplumber
from loguru import logger


def extract_pdf(source: str | Path | bytes) -> List[Dict[str, Any]]:
    """
    Extract text and tables from a PDF.

    Args:
        source: file path, URL string (bytes already downloaded), or raw bytes

    Returns:
        List of page-level content dicts:
        {
          "page": int,
          "type": "text" | "table",
          "content": str,   # plain text or markdown table
        }
    """
    if isinstance(source, (str, Path)):
        raw_bytes = Path(source).read_bytes()
    else:
        raw_bytes = source

    results: List[Dict[str, Any]] = []

    # ── PyMuPDF: text extraction ────────────────────────────────
    try:
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                results.append({"page": page_num, "type": "text", "content": text})
        doc.close()
    except Exception as e:
        logger.warning(f"PyMuPDF extraction failed: {e}")

    # ── pdfplumber: table extraction ────────────────────────────
    try:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table in tables:
                    md = _table_to_markdown(table)
                    if md:
                        results.append({"page": page_num, "type": "table", "content": md})
    except Exception as e:
        logger.warning(f"pdfplumber table extraction failed: {e}")

    logger.info(f"PDF extracted: {len(results)} blocks from {sum(1 for r in results if r['type']=='text')} text pages")
    return results


def _table_to_markdown(table: List[List]) -> str:
    """Convert pdfplumber table (list of lists) → markdown table string."""
    if not table or not table[0]:
        return ""

    # Clean None cells
    cleaned = [[str(cell or "").strip() for cell in row] for row in table]
    header = cleaned[0]
    rows = cleaned[1:]

    col_widths = [max(len(h), max((len(r[i]) for r in rows if i < len(r)), default=0)) for i, h in enumerate(header)]

    def fmt_row(cells):
        return "| " + " | ".join(c.ljust(col_widths[i]) if i < len(col_widths) else c for i, c in enumerate(cells)) + " |"

    lines = [fmt_row(header), "| " + " | ".join("-" * w for w in col_widths) + " |"]
    for row in rows:
        lines.append(fmt_row(row))

    return "\n".join(lines)

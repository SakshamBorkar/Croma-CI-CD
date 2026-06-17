"""
app/ingestion/chunker.py
─────────────────────────
Splits extracted content into chunks with full metadata.
Implements the metadata schema from the spec (Layer 2c).

Special rules:
  - Tables: kept as single chunks (never split mid-row)
  - Financial figures: never split mid-row
  - Chunk size: 500 tokens / 50-token overlap (approx 4 chars/token)
"""

import hashlib
from datetime import date
from typing import Any, Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from app.core.config import settings

# Approx 4 chars per token → 500 tokens ≈ 2000 chars
CHARS_PER_TOKEN = 4
CHUNK_SIZE_CHARS = settings.CHUNK_SIZE * CHARS_PER_TOKEN
CHUNK_OVERLAP_CHARS = settings.CHUNK_OVERLAP * CHARS_PER_TOKEN

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE_CHARS,
    chunk_overlap=CHUNK_OVERLAP_CHARS,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)


def chunk_document(
    content_blocks: List[Dict[str, Any]],
    competitor: str,
    source_type: str,
    source_url: str,
    publication_date: Optional[str] = None,
    ci_dimensions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Take extracted content blocks (from pdf_extractor or scraper) and
    produce chunked dicts with full metadata schema.

    Returns:
        List of chunk dicts, each with:
          text, competitor, source_type, source_url, publication_date,
          ingestion_date, ci_dimensions, chunk_index, content_hash, block_type
    """
    today = date.today().isoformat()
    all_chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    for block in content_blocks:
        block_type = block.get("type", "text")
        text = block.get("content", "").strip()

        if not text:
            continue

        if block_type == "table":
            # Tables: keep as a single chunk — never split
            chunks = [text]
        else:
            chunks = _splitter.split_text(text)

        for chunk_text in chunks:
            chunk_text = chunk_text.strip()
            if not chunk_text or len(chunk_text) < 50:
                continue

            content_hash = hashlib.md5(chunk_text.encode()).hexdigest()
            dims = ci_dimensions or _auto_classify_dimensions(chunk_text)

            all_chunks.append({
                "text": chunk_text,
                # ── Metadata schema (Layer 2c) ──────────────────
                "competitor": competitor,
                "source_type": source_type,
                "source_url": source_url,
                "publication_date": publication_date or today,
                "ingestion_date": today,
                "ci_dimensions": dims,
                "chunk_index": chunk_index,
                "content_hash": content_hash,
                "block_type": block_type,   # extra: text | table
                "page": block.get("page"),
            })
            chunk_index += 1

    logger.info(f"Chunker: {len(content_blocks)} blocks → {len(all_chunks)} chunks for {competitor}/{source_type}")
    return all_chunks


# ─── Heuristic dimension classifier ─────────────────────────────
_DIMENSION_KEYWORDS = {
    "business_model": [
        "channel", "online", "offline", "b2b", "emi", "bnpl", "warranty",
        "after-sales", "supply chain", "app", "loyalty", "portfolio",
    ],
    "geographical_presence": [
        "store", "outlet", "city", "state", "expansion", "location",
        "square feet", "sq.ft", "footprint", "franchise", "metro",
    ],
    "financial_performance": [
        "revenue", "ebitda", "profit", "loss", "margin", "crore", "turnover",
        "balance sheet", "debt", "credit", "rating", "annual report",
    ],
    "customer_feedback": [
        "rating", "review", "nps", "complaint", "feedback", "customer",
        "satisfaction", "app store", "google reviews", "trustpilot",
    ],
    "strategic_initiatives": [
        "acquisition", "investment", "partnership", "leadership", "ceo",
        "md", "fundraise", "technology", "sustainability", "esg",
    ],
    "future_outlook": [
        "guidance", "forecast", "analyst", "target price", "expansion",
        "plan", "next year", "upcoming", "announced",
    ],
}


def _auto_classify_dimensions(text: str) -> List[str]:
    text_lower = text.lower()
    matched = []
    for dim, keywords in _DIMENSION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(dim)
    return matched if matched else ["general"]

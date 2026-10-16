"""
app/ingestion/document_processor.py
───────────────────────────────────
Full-featured document processing pipeline:
  1. Content & extension validation (PDF, DOCX, DOC, TXT, MD, CSV, XLSX, XLS).
  2. Structural & page-preserving text extraction.
  3. Table preservation (PDF, Word, CSV, Excel).
  4. Semantically useful chunking with metadata (doc_id, page, section, hash).
  5. Embedding and indexing into ChromaDB (croma_user_documents).
  6. Document isolation per user/session.
  7. Registry management and cleanup on deletion.
"""

import csv
import hashlib
import io
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.core.config import settings
from app.ingestion.embedder import embed_chunks_batch
from app.ingestion.upserter import get_chroma_client

# ── Limits & Configuration ──────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
MAX_DOCUMENTS_PER_USER = 50
UPLOAD_DIR = Path(getattr(settings, "UPLOAD_DIR", "./uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY_FILE = UPLOAD_DIR / "documents_registry.json"

USER_DOCS_COLLECTION_NAME = f"{settings.CHROMA_COLLECTION_PREFIX}_user_documents"

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".txt",
    ".md",
    ".csv",
    ".xlsx",
    ".xls",
}


# ── Registry Helpers (Persistent JSON + Thread-safe) ────────────────
def _load_registry() -> Dict[str, Dict[str, Any]]:
    if not REGISTRY_FILE.exists():
        return {}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load registry: {e}")
        return {}


def _save_registry(registry: Dict[str, Dict[str, Any]]) -> None:
    try:
        temp_file = REGISTRY_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, default=str)
        temp_file.replace(REGISTRY_FILE)
    except Exception as e:
        logger.error(f"Failed to save registry: {e}")


# ── File Validation ─────────────────────────────────────────────────
def validate_file(file_bytes: bytes, filename: str) -> Tuple[bool, str, str]:
    """
    Validates file extension, size, and content signatures (magic bytes).
    Returns (is_valid, error_message, detected_extension).
    """
    if not filename or "." not in filename:
        return False, "File must have a valid extension.", ""

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return (
            False,
            f"Unsupported format '{ext}'. Supported: PDF, Word (docx/doc), Text/Markdown (txt/md), CSV, Excel (xlsx/xls).",
            "",
        )

    size = len(file_bytes)
    if size == 0:
        return False, "File is empty (0 bytes).", ""
    if size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        return False, f"File exceeds maximum allowed size of {max_mb:.0f} MB.", ""

    # Signature / Magic bytes inspection
    # Executable inspection (DOS PE / ELF / Mach-O)
    if file_bytes.startswith(b"MZ"):
        return False, "Executable binary files (.exe / .dll) are strictly prohibited.", ""
    if file_bytes.startswith(b"\x7fELF"):
        return False, "ELF binary executables are strictly prohibited.", ""

    # Specific format signature verification
    if ext == ".pdf":
        if not file_bytes.startswith(b"%PDF"):
            return False, "Malformed PDF: File header does not match PDF specification.", ""
    elif ext in (".docx", ".xlsx"):
        # docx and xlsx are ZIP containers (PK\x03\x04)
        if not file_bytes.startswith(b"PK\x03\x04"):
            return False, f"Malformed {ext.upper()}: File is corrupted or not a valid Office Open XML container.", ""

    return True, "", ext


# ── Text & Structure Extraction ─────────────────────────────────────
def extract_document_pages(
    file_bytes: bytes, filename: str, ext: str
) -> List[Dict[str, Any]]:
    """
    Extracts text, preserving page numbers, section headers, and tabular structures.
    Returns list of blocks:
      [{ "text": str, "page_number": int | None, "section": str | None }]
    """
    blocks: List[Dict[str, Any]] = []

    if ext == ".pdf":
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_num = page_idx + 1
            text = page.get_text("text").strip()

            # Also attempt table extraction via PyMuPDF find_tables if present
            tables_text = []
            try:
                tabs = page.find_tables()
                for tab in tabs:
                    df = tab.extract()
                    if df and len(df) > 1:
                        table_md = "\n".join([" | ".join(str(cell or "").strip() for cell in row) for row in df])
                        tables_text.append(f"Table:\n{table_md}")
            except Exception:
                pass

            combined_text = text
            if tables_text:
                combined_text += "\n\n" + "\n\n".join(tables_text)

            if combined_text.strip():
                blocks.append({
                    "text": combined_text.strip(),
                    "page_number": page_num,
                    "section": f"Page {page_num}",
                })
        doc.close()

    elif ext == ".docx":
        import docx

        doc = docx.Document(io.BytesIO(file_bytes))
        current_section = "Introduction"
        current_text_parts: List[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style.name.startswith("Heading"):
                if current_text_parts:
                    blocks.append({
                        "text": "\n".join(current_text_parts),
                        "page_number": None,
                        "section": current_section,
                    })
                    current_text_parts = []
                current_section = text
            else:
                current_text_parts.append(text)

        # Extract docx tables with headers preserved
        for t_idx, table in enumerate(doc.tables):
            rows_data = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells]
                rows_data.append(" | ".join(row_cells))
            if rows_data:
                table_md = f"Table {t_idx + 1}:\n" + "\n".join(rows_data)
                current_text_parts.append(table_md)

        if current_text_parts:
            blocks.append({
                "text": "\n".join(current_text_parts),
                "page_number": None,
                "section": current_section,
            })

    elif ext == ".doc":
        # Legacy binary Word doc fallback text extraction
        text = file_bytes.decode("latin-1", errors="ignore")
        # Extract printable ASCII sequences
        clean_text = "\n".join(re.findall(r"[\x20-\x7E]{4,}", text))
        if clean_text.strip():
            blocks.append({
                "text": clean_text[:50000],
                "page_number": None,
                "section": "Legacy DOC Content",
            })
        else:
            raise ValueError("Could not extract readable text from legacy .doc file. Please convert to .docx.")

    elif ext in (".csv", ".txt", ".md"):
        content_str = file_bytes.decode("utf-8", errors="replace")
        if ext == ".csv":
            # Preserve headers and rows
            reader = csv.reader(io.StringIO(content_str))
            rows = list(reader)
            if rows:
                headers = rows[0]
                md_lines = [" | ".join(headers), " | ".join(["---"] * len(headers))]
                for r in rows[1:500]:  # Up to 500 rows
                    md_lines.append(" | ".join(r))
                blocks.append({
                    "text": "\n".join(md_lines),
                    "page_number": 1,
                    "section": "CSV Table",
                })
        else:
            # Markdown / TXT: chunk by headers or paragraphs
            sections = re.split(r"(?m)^(?=#{1,3}\s)", content_str)
            for s_idx, sec in enumerate(sections):
                s_text = sec.strip()
                if not s_text:
                    continue
                first_line = s_text.split("\n")[0].replace("#", "").strip() or f"Section {s_idx + 1}"
                blocks.append({
                    "text": s_text,
                    "page_number": None,
                    "section": first_line[:60],
                })

    elif ext in (".xlsx", ".xls"):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            rows_data = []
            for row in sheet.iter_rows(values_only=True):
                if any(row):
                    rows_data.append(" | ".join(str(c or "").strip() for c in row))
            if rows_data:
                table_md = f"Sheet: {sheet_name}\n" + "\n".join(rows_data[:500])
                blocks.append({
                    "text": table_md,
                    "page_number": None,
                    "section": f"Sheet: {sheet_name}",
                })

    return blocks


# ── Chunking Pipeline ───────────────────────────────────────────────
def chunk_document_blocks(
    blocks: List[Dict[str, Any]],
    doc_id: str,
    user_id: str,
    filename: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List[Dict[str, Any]]:
    """
    Splits blocks into semantic chunks while preserving document ID,
    page number, section name, content hash, and user ID.
    """
    chunks: List[Dict[str, Any]] = []
    chunk_idx = 0

    for block in blocks:
        text = block["text"]
        page_num = block.get("page_number")
        section = block.get("section") or "General"

        # Split long text
        if len(text) <= chunk_size:
            pieces = [text]
        else:
            pieces = []
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                pieces.append(text[start:end])
                if end == len(text):
                    break
                start += chunk_size - chunk_overlap

        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue

            content_hash = hashlib.sha256(piece.encode("utf-8")).hexdigest()
            chunk_obj = {
                "id": f"{doc_id}_{chunk_idx}",
                "doc_id": doc_id,
                "user_id": user_id,
                "filename": filename,
                "page_number": page_num,
                "section": section,
                "chunk_index": chunk_idx,
                "text": piece,
                "content_hash": content_hash,
                "source_type": "uploaded_document",
            }
            chunks.append(chunk_obj)
            chunk_idx += 1

    return chunks


# ── ChromaDB Indexing ───────────────────────────────────────────────
def get_user_docs_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=USER_DOCS_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


async def index_document_chunks(chunks: List[Dict[str, Any]]) -> int:
    """
    Embeds chunks and indexes them into ChromaDB under USER_DOCS_COLLECTION_NAME.
    """
    if not chunks:
        return 0

    collection = get_user_docs_collection()
    texts = [c["text"] for c in chunks]

    # Generate embeddings with local ONNX/Ollama embedder
    embedded_chunks = await embed_chunks_batch(chunks)

    ids = [c["id"] for c in embedded_chunks]
    embeddings = [c["embedding"] for c in embedded_chunks]
    docs = [c["text"] for c in embedded_chunks]
    metadatas = [
        {
            "doc_id": str(c["doc_id"]),
            "user_id": str(c["user_id"]),
            "filename": str(c["filename"]),
            "page_number": int(c["page_number"]) if c.get("page_number") is not None else -1,
            "section": str(c.get("section") or ""),
            "chunk_index": int(c["chunk_index"]),
            "content_hash": str(c["content_hash"]),
            "source_type": "uploaded_document",
        }
        for c in embedded_chunks
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=docs,
        metadatas=metadatas,
    )
    logger.info(f"Successfully indexed {len(ids)} chunks for document {chunks[0]['doc_id']} in ChromaDB")
    return len(ids)


# ── Document Lifecycle (Upload, Delete, Preview) ────────────────────
async def process_and_register_document(
    file_bytes: bytes,
    filename: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    End-to-end processing pipeline:
      1. Validate file format and size
      2. Store securely on disk
      3. Extract text and pages
      4. Chunk and embed
      5. Index in ChromaDB
      6. Record in registry
    """
    is_valid, err_msg, ext = validate_file(file_bytes, filename)
    if not is_valid:
        raise ValueError(err_msg)

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    safe_name = re.sub(r"[^\w\.-]", "_", filename)
    storage_filename = f"{doc_id}_{safe_name}"
    storage_path = UPLOAD_DIR / storage_filename

    # Save to disk securely
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    # Initial registry entry
    registry = _load_registry()
    now_iso = datetime.utcnow().isoformat()
    record: Dict[str, Any] = {
        "document_id": doc_id,
        "user_id": user_id,
        "filename": filename,
        "file_type": ext.lstrip("."),
        "file_size": len(file_bytes),
        "storage_path": str(storage_path),
        "created_at": now_iso,
        "status": "processing",
        "stage": "extracting",
        "chunk_count": 0,
        "page_count": 0,
        "error_message": None,
    }
    registry[doc_id] = record
    _save_registry(registry)

    try:
        # Step 2: Extract text & structure
        blocks = extract_document_pages(file_bytes, filename, ext)
        if not blocks:
            raise ValueError(f"No text could be extracted from {filename}.")

        page_count = max([b.get("page_number") or 1 for b in blocks])
        record["stage"] = "chunking"
        _save_registry(registry)

        # Step 3: Chunking
        chunks = chunk_document_blocks(blocks, doc_id, user_id, filename)
        record["stage"] = "embedding"
        _save_registry(registry)

        # Step 4: Embedding & Indexing into ChromaDB
        indexed_count = await index_document_chunks(chunks)
        record["stage"] = "ready"
        record["status"] = "ready"
        record["chunk_count"] = indexed_count
        record["page_count"] = page_count
        _save_registry(registry)

        logger.info(f"Document {doc_id} ({filename}) ready with {indexed_count} indexed chunks")
        return record

    except Exception as e:
        logger.error(f"Failed processing document {filename}: {e}")
        record["status"] = "failed"
        record["stage"] = "error"
        record["error_message"] = str(e)
        _save_registry(registry)
        raise e


def list_user_documents(user_id: str) -> List[Dict[str, Any]]:
    """List all documents belonging to the user."""
    registry = _load_registry()
    docs = [doc for doc in registry.values() if doc.get("user_id") == user_id]
    # Sort newest first
    docs.sort(key=lambda d: d.get("created_at", ""), reverse=True)
    return docs


def get_user_document(document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific document belonging to user."""
    registry = _load_registry()
    doc = registry.get(document_id)
    if doc and doc.get("user_id") == user_id:
        return doc
    return None


def delete_user_document(document_id: str, user_id: str) -> bool:
    """
    Deletes document file, ChromaDB chunk records, and registry entry.
    """
    registry = _load_registry()
    doc = registry.get(document_id)
    if not doc or doc.get("user_id") != user_id:
        return False

    # 1. Delete ChromaDB chunks
    try:
        collection = get_user_docs_collection()
        collection.delete(where={"doc_id": document_id})
        logger.info(f"Deleted ChromaDB chunks for document {document_id}")
    except Exception as e:
        logger.warning(f"Failed deleting chunks from ChromaDB for {document_id}: {e}")

    # 2. Delete file from disk
    storage_path = Path(doc.get("storage_path", ""))
    if storage_path.exists():
        try:
            storage_path.unlink()
        except Exception as e:
            logger.warning(f"Could not remove file {storage_path}: {e}")

    # 3. Remove from registry
    del registry[document_id]
    _save_registry(registry)
    return True


def get_document_preview(document_id: str, user_id: str, max_chars: int = 15000) -> Optional[Dict[str, Any]]:
    """
    Returns preview text and structure for citations / document preview drawer.
    """
    doc = get_user_document(document_id, user_id)
    if not doc:
        return None

    storage_path = Path(doc["storage_path"])
    if not storage_path.exists():
        return None

    try:
        with open(storage_path, "rb") as f:
            file_bytes = f.read()

        ext = f".{doc['file_type']}"
        blocks = extract_document_pages(file_bytes, doc["filename"], ext)
        full_text = "\n\n".join(b["text"] for b in blocks)

        return {
            "document_id": document_id,
            "filename": doc["filename"],
            "file_type": doc["file_type"],
            "file_size": doc["file_size"],
            "page_count": doc.get("page_count", len(blocks)),
            "sections": [b.get("section") for b in blocks if b.get("section")],
            "preview_text": full_text[:max_chars],
        }
    except Exception as e:
        logger.error(f"Error generating preview for {document_id}: {e}")
        return None


async def retrieve_user_documents(
    query: str,
    user_id: str,
    selected_doc_ids: Optional[List[str]] = None,
    top_k: int = 8,
) -> List[Dict[str, Any]]:
    """
    Retrieves relevant passages from uploaded user documents using hybrid dense + BM25 ranking.
    Restricts search strictly to the current user's documents and optional selected_doc_ids.
    """
    from rank_bm25 import BM25Okapi
    from app.ingestion.embedder import embed_single_async

    collection = get_user_docs_collection()
    if collection.count() == 0:
        return []

    query_embedding = await embed_single_async(query)

    # Build Chroma metadata filter for user isolation
    where_filter: Dict[str, Any]
    if selected_doc_ids and len(selected_doc_ids) > 0:
        if len(selected_doc_ids) == 1:
            where_filter = {
                "$and": [
                    {"user_id": user_id},
                    {"doc_id": selected_doc_ids[0]},
                ]
            }
        else:
            where_filter = {
                "$and": [
                    {"user_id": user_id},
                    {"doc_id": {"$in": selected_doc_ids}},
                ]
            }
    else:
        where_filter = {"user_id": user_id}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k * 2, max(collection.count(), 1)),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.warning(f"Error querying user documents collection: {e}")
        return []

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]
    dists = results.get("distances", [[]])[0]

    if not docs:
        return []

    # BM25 Sparse Re-ranking over dense candidates
    tokenized_corpus = [d.lower().split() for d in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query.lower().split())

    scored_candidates = []
    for i in range(len(docs)):
        meta = metas[i]
        page = meta.get("page_number", -1)
        section = meta.get("section", "")
        filename = meta.get("filename", "Uploaded Document")

        # Human-readable citation formatting
        if page and int(page) > 0:
            citation_label = f"[{filename}, p. {page}]"
        elif section and section != "General":
            citation_label = f"[{filename}, {section}]"
        else:
            citation_label = f"[{filename}]"

        dense_score = max(0.0, 1.0 - float(dists[i])) if i < len(dists) else 0.5
        sparse_score = float(bm25_scores[i]) if i < len(bm25_scores) else 0.0
        combined_score = 0.6 * dense_score + 0.4 * min(sparse_score / 10.0, 1.0)

        meta_with_citation = dict(meta)
        meta_with_citation["citation_label"] = citation_label

        scored_candidates.append({
            "id": ids[i],
            "text": docs[i],
            "score": round(combined_score, 3),
            "metadata": meta_with_citation,
            "filename": filename,
            "page_number": page if page > 0 else None,
            "section": section,
            "citation_label": citation_label,
            "source_type": "uploaded_document",
        })

    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    return scored_candidates[:top_k]


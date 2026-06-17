"""
app/ingestion/upserter.py
──────────────────────────
ChromaDB vector store operations.
  - One collection per competitor (mirrors Pinecone namespace design)
  - Metadata filtering on ci_dimensions, source_type, publication_date
  - Deduplication via content_hash

ChromaDB runs locally (file-based persistence).
For cloud deployment, swap to Pinecone by changing this module only.

Setup: `pip install chromadb` (already in requirements.txt)
"""

import json
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger

from app.core.config import settings

# ─── Singleton ChromaDB client ────────────────────────────────────
_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialised at {settings.CHROMA_PERSIST_DIR}")
    return _client


def _collection_name(competitor: str) -> str:
    return f"{settings.CHROMA_COLLECTION_PREFIX}_{competitor}"


def get_or_create_collection(competitor: str) -> chromadb.Collection:
    client = get_chroma_client()
    name = _collection_name(competitor)
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ─── Upsert ──────────────────────────────────────────────────────
def upsert_chunks(chunks: List[Dict[str, Any]], competitor: str) -> int:
    """
    Upsert embedded chunks into ChromaDB collection.
    Deduplicates by content_hash (used as document ID).
    Returns number of new chunks inserted.
    """
    collection = get_or_create_collection(competitor)
    existing_ids = set(collection.get(include=[])["ids"])

    new_ids, new_docs, new_embeddings, new_metas = [], [], [], []

    for chunk in chunks:
        doc_id = chunk["content_hash"]
        if doc_id in existing_ids:
            continue  # already indexed

        meta = {
            "competitor": chunk.get("competitor", competitor),
            "source_type": chunk.get("source_type", ""),
            "source_url": chunk.get("source_url", ""),
            "publication_date": str(chunk.get("publication_date", "")),
            "ingestion_date": str(chunk.get("ingestion_date", "")),
            "ci_dimensions": json.dumps(chunk.get("ci_dimensions", [])),
            "chunk_index": int(chunk.get("chunk_index", 0)),
            "block_type": chunk.get("block_type", "text"),
        }

        new_ids.append(doc_id)
        new_docs.append(chunk["text"])
        new_embeddings.append(chunk["embedding"])
        new_metas.append(meta)

    if new_ids:
        collection.add(
            ids=new_ids,
            documents=new_docs,
            embeddings=new_embeddings,
            metadatas=new_metas,
        )
        logger.info(f"Upserted {len(new_ids)} new chunks for {competitor}")
    else:
        logger.info(f"No new chunks for {competitor} (all duplicates)")

    return len(new_ids)


# ─── Query ───────────────────────────────────────────────────────
def query_collection(
    competitor: str,
    query_embedding: List[float],
    top_k: int = settings.TOP_K_RETRIEVE,
    source_type_filter: Optional[str] = None,
    ci_dimension_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Dense vector search in a competitor's collection.
    Returns top_k results with text + metadata.
    """
    collection = get_or_create_collection(competitor)
    
    # We filter by ci_dimension in Python because ChromaDB doesn't support substring/$contains on strings.
    where_clause = _build_where(source_type_filter, date_from, date_to)

    kwargs = dict(
        query_embeddings=[query_embedding],
        n_results=min(top_k * 2 if ci_dimension_filter else top_k, max(1, collection.count())), # fetch more if we need to filter
        include=["documents", "metadatas", "distances"],
    )
    if where_clause:
        kwargs["where"] = where_clause

    results = collection.query(**kwargs)

    hits = []
    for i, doc_id in enumerate(results["ids"][0]):
        hits.append({
            "id": doc_id,
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
            "score": 1 - results["distances"][0][i],  # cosine → similarity
        })
        
    # Post-filtering by dimension in Python
    if ci_dimension_filter:
        import json
        filtered_hits = []
        for h in hits:
            dims_str = h["metadata"].get("ci_dimensions", "[]")
            try:
                dims = json.loads(dims_str)
            except Exception:
                dims = []
            # Match if the specific dimension is present, or if it is classified as general
            if ci_dimension_filter in dims or "general" in dims:
                filtered_hits.append(h)
        hits = filtered_hits

    return hits[:top_k]


def query_all_competitors(
    query_embedding: List[float],
    top_k: int = settings.TOP_K_RETRIEVE,
    competitors: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Query all competitor collections and merge results."""
    targets = competitors or settings.COMPETITORS
    all_hits = []
    for comp in targets:
        try:
            hits = query_collection(comp, query_embedding, top_k=top_k)
            for h in hits:
                h["metadata"]["competitor"] = comp
            all_hits.extend(hits)
        except Exception as e:
            logger.warning(f"Query failed for {comp}: {e}")

    all_hits.sort(key=lambda x: x["score"], reverse=True)
    return all_hits[:top_k]


def collection_stats(competitor: str) -> Dict[str, Any]:
    """Return count + metadata for a competitor collection."""
    collection = get_or_create_collection(competitor)
    return {"competitor": competitor, "chunk_count": collection.count()}


# ─── Where clause builder ─────────────────────────────────────────
def _build_where(
    source_type: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
) -> Optional[Dict]:
    conditions = []
    if source_type:
        conditions.append({"source_type": {"$eq": source_type}})
    if date_from:
        conditions.append({"publication_date": {"$gte": date_from}})
    if date_to:
        conditions.append({"publication_date": {"$lte": date_to}})

    if len(conditions) == 0:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}

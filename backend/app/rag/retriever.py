"""
app/rag/retriever.py
─────────────────────
Hybrid retrieval:
  1. Dense: ChromaDB cosine similarity (Ollama embeddings)
  2. Sparse: BM25 over the retrieved candidates
  3. Fusion: Reciprocal Rank Fusion (RRF)

No Pinecone or Cohere — runs fully locally.
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.ingestion.embedder import embed_single_async
from app.ingestion.upserter import query_collection, query_all_competitors


async def retrieve(
    query: str,
    competitor: Optional[str] = None,
    top_k_dense: int = settings.TOP_K_RETRIEVE,
    top_k_final: int = settings.TOP_K_RERANK,
    source_type_filter: Optional[str] = None,
    ci_dimension_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Full hybrid retrieval pipeline.

    Returns top_k_final chunks ranked by RRF(dense, BM25).
    """
    # Step 1: embed query
    query_embedding = await embed_single_async(query)

    # Step 2: dense retrieval
    if competitor:
        dense_hits = query_collection(
            competitor,
            query_embedding,
            top_k=top_k_dense,
            source_type_filter=source_type_filter,
            ci_dimension_filter=ci_dimension_filter,
            date_from=date_from,
            date_to=date_to,
        )
    else:
        dense_hits = query_all_competitors(query_embedding, top_k=top_k_dense)

    if not dense_hits:
        logger.warning(f"No dense hits for query: {query[:60]}")
        return []

    # Step 3: BM25 sparse retrieval over dense candidates
    corpus = [h["text"] for h in dense_hits]
    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = query.lower().split()
    bm25_scores = bm25.get_scores(query_tokens)

    # Step 4: RRF fusion
    ranked = _rrf_fusion(dense_hits, bm25_scores)

    logger.info(f"Retriever: {len(dense_hits)} dense → {len(ranked)} RRF ranked → returning top {top_k_final}")
    return ranked[:top_k_final]


def _rrf_fusion(
    dense_hits: List[Dict[str, Any]],
    bm25_scores: List[float],
    k: int = 60,
    dense_weight: float = settings.DENSE_WEIGHT,
    bm25_weight: float = settings.BM25_WEIGHT,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion of dense and sparse results.
    RRF score = dense_weight / (k + dense_rank) + bm25_weight / (k + bm25_rank)
    """
    # Dense rankings (already sorted by score desc)
    dense_ranks = {h["id"]: i + 1 for i, h in enumerate(dense_hits)}

    # BM25 rankings
    bm25_ranked = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
    bm25_ranks = {dense_hits[i]["id"]: rank + 1 for rank, i in enumerate(bm25_ranked)}

    rrf_scores = {}
    for hit in dense_hits:
        doc_id = hit["id"]
        dr = dense_ranks.get(doc_id, len(dense_hits) + 1)
        br = bm25_ranks.get(doc_id, len(dense_hits) + 1)
        rrf_scores[doc_id] = dense_weight / (k + dr) + bm25_weight / (k + br)

    sorted_hits = sorted(dense_hits, key=lambda h: rrf_scores.get(h["id"], 0), reverse=True)

    # Attach RRF score for transparency
    for h in sorted_hits:
        h["rrf_score"] = rrf_scores.get(h["id"], 0)

    return sorted_hits

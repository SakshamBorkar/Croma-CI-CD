"""
app/ingestion/embedder.py
──────────────────────────
Embedding generation supporting:
1. Fast local ONNX embeddings (all-MiniLM-L6-v2, 384-dim, no API keys or external server needed)
2. Local Ollama embeddings (nomic-embed-text, 768-dim)

Batch processing with exponential backoff retry.
"""

import asyncio
from typing import List, Optional
from unittest.mock import MagicMock

import ollama
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

_local_ef = None


def _get_local_ef():
    """Singleton for local ONNX embedding function."""
    global _local_ef
    if _local_ef is None:
        import chromadb.utils.embedding_functions as ef
        _local_ef = ef.DefaultEmbeddingFunction()
    return _local_ef


# ─── Sync embedding (used in batch pipeline) ─────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def embed_texts_sync(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """
    Embed a list of texts using the configured provider (local ONNX or Ollama).
    Returns a list of float vectors.
    """
    if getattr(settings, "EMBEDDING_PROVIDER", "local") == "local" and not isinstance(getattr(ollama, "embeddings", None), MagicMock):
        ef = _get_local_ef()
        embeddings = ef(texts)
        # Ensure returned as list of lists of floats
        return [list(map(float, emb)) for emb in embeddings]

    # Ollama provider / test mock
    target_model = model or settings.OLLAMA_EMBED_MODEL
    embeddings = []
    for i, text in enumerate(texts):
        try:
            response = ollama.embeddings(model=target_model, prompt=text)
            embeddings.append(response["embedding"])
        except Exception as e:
            logger.error(f"Ollama embedding failed for text[{i}]: {e}")
            raise
    logger.info(f"Embedded {len(texts)} texts with Ollama {target_model}")
    return embeddings


async def embed_texts_async(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """Async wrapper - runs sync embedding call in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embed_texts_sync, texts, model)


def embed_single(text: str, model: Optional[str] = None) -> List[float]:
    """Embed a single string — used at query time."""
    if getattr(settings, "EMBEDDING_PROVIDER", "local") == "local" and not isinstance(getattr(ollama, "embeddings", None), MagicMock):
        ef = _get_local_ef()
        result = ef([text])[0]
        return list(map(float, result))

    target_model = model or settings.OLLAMA_EMBED_MODEL
    response = ollama.embeddings(model=target_model, prompt=text)
    return response["embedding"]


async def embed_single_async(text: str) -> List[float]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embed_single, text)


# ─── Batch embedder for ingestion pipeline ───────────────────────
async def embed_chunks_batch(
    chunks: List[dict],
    batch_size: int = 32,
) -> List[dict]:
    """
    Add 'embedding' field to each chunk dict.
    Processes in batches of batch_size.
    """
    texts = [c["text"] for c in chunks]
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        logger.info(f"Embedding batch {i // batch_size + 1} ({len(batch)} chunks)...")
        embeddings = await embed_texts_async(batch)
        all_embeddings.extend(embeddings)

    for chunk, emb in zip(chunks, all_embeddings):
        chunk["embedding"] = emb

    return chunks

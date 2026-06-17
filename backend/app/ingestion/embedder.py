"""
app/ingestion/embedder.py
──────────────────────────
Embedding generation using Ollama (local, no API key needed).

Default model: nomic-embed-text (768-dim, runs on CPU/GPU)
Alternatives:  mxbai-embed-large (1024-dim), all-minilm (384-dim)

Run once before starting:
    ollama pull nomic-embed-text

Batch processing with exponential backoff retry.
"""

import asyncio
from typing import List

import ollama
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


# ─── Sync embedding (used in batch pipeline) ─────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def embed_texts_sync(texts: List[str], model: str = settings.OLLAMA_EMBED_MODEL) -> List[List[float]]:
    """
    Embed a list of texts using Ollama.
    Returns a list of float vectors.

    Ollama processes one at a time; we batch manually.
    """
    embeddings = []
    for i, text in enumerate(texts):
        try:
            response = ollama.embeddings(model=model, prompt=text)
            embeddings.append(response["embedding"])
        except Exception as e:
            logger.error(f"Embedding failed for text[{i}]: {e}")
            raise
    logger.info(f"Embedded {len(texts)} texts with {model}")
    return embeddings


async def embed_texts_async(texts: List[str], model: str = settings.OLLAMA_EMBED_MODEL) -> List[List[float]]:
    """Async wrapper - runs sync Ollama call in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embed_texts_sync, texts, model)


def embed_single(text: str, model: str = settings.OLLAMA_EMBED_MODEL) -> List[float]:
    """Embed a single string — used at query time."""
    response = ollama.embeddings(model=model, prompt=text)
    return response["embedding"]


async def embed_single_async(text: str) -> List[float]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embed_single, text)


# ─── Batch embedder for ingestion pipeline ───────────────────────
async def embed_chunks_batch(
    chunks: List[dict],
    batch_size: int = 32,    # Ollama handles smaller batches well
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

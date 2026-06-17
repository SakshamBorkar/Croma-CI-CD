"""
app/rag/decomposer.py
──────────────────────
Query decomposition: breaks a complex NL query into sub-queries
per competitor + CI dimension for targeted retrieval.

Uses Ollama LLM to generate sub-queries (no OpenAI needed).
"""

import json
from typing import Any, Dict, List, Optional

import ollama
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

DECOMPOSE_PROMPT = """You are a search query expert for a competitive intelligence system about Indian electronics retailers.

Given the user query below, decompose it into 2-5 specific search sub-queries.
Each sub-query should be focused and retrievable from documents.

User query: {query}

Competitors available: {competitors}
CI dimensions: {dimensions}

Return ONLY a JSON array of sub-query strings. No explanation. Example:
["Vijay Sales store count Maharashtra 2024", "Vijay Sales new store openings 2024", "Reliance Digital store expansion 2024"]
"""


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
def decompose_query(query: str, competitors: Optional[List[str]] = None) -> List[str]:
    """
    Decompose a user query into targeted sub-queries.
    Falls back to the original query if decomposition fails.
    """
    comp_list = competitors or settings.COMPETITORS
    dim_list = settings.CI_DIMENSIONS

    prompt = DECOMPOSE_PROMPT.format(
        query=query,
        competitors=", ".join(comp_list),
        dimensions=", ".join(dim_list),
    )

    try:
        response = ollama.chat(
            model=settings.OLLAMA_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0, "num_predict": 300},
        )
        raw = response["message"]["content"].strip()

        # Extract JSON array from response
        start, end = raw.find("["), raw.rfind("]") + 1
        if start >= 0 and end > start:
            sub_queries = json.loads(raw[start:end])
            if isinstance(sub_queries, list) and sub_queries:
                logger.info(f"Decomposed into {len(sub_queries)} sub-queries")
                return sub_queries

    except Exception as e:
        logger.warning(f"Query decomposition failed: {e}. Using original query.")

    return [query]  # fallback: use original query as-is


async def decompose_query_async(query: str, competitors: Optional[List[str]] = None) -> List[str]:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, decompose_query, query, competitors)

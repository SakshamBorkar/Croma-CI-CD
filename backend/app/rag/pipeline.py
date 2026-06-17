"""
app/rag/pipeline.py
────────────────────
Full RAG pipeline orchestrator.

Flow:
  query → decompose → [sub-query → retrieve → generate] → merge → return

Also exposes:
  - full_competitor_report: generate all dimensions for one competitor
  - compare: compare all competitors for one dimension
"""

import asyncio
from datetime import date
from typing import Any, Dict, List, Optional

from loguru import logger

from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.rag.decomposer import decompose_query_async
from app.rag.generator import generate_answer_async
from app.rag.retriever import retrieve


async def run_query(
    query: str,
    competitor: Optional[str] = None,
    ci_dimension: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Main entry point: free-form NL query with optional filters.
    Returns merged answer from all sub-queries.
    """
    cache_key_extra = f"{competitor or 'all'}::{ci_dimension or 'all'}"

    if use_cache:
        cached = await cache_get(query, cache_key_extra)
        if cached:
            return cached

    # Step 1: Decompose
    sub_queries = await decompose_query_async(query, competitors=[competitor] if competitor else None)

    # Step 2: Retrieve + Generate for each sub-query (concurrent)
    tasks = []
    for sq in sub_queries:
        tasks.append(
            _retrieve_and_generate(sq, competitor, ci_dimension or "general")
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid_results = [r for r in results if isinstance(r, dict)]

    if not valid_results:
        return {"error": "No results found", "query": query}

    # Step 3: Merge sub-results
    merged = _merge_results(valid_results, original_query=query)

    if use_cache:
        await cache_set(query, merged, cache_key_extra)

    return merged


_ollama_semaphore = asyncio.Semaphore(1)


async def _retrieve_and_generate(
    query: str, competitor: Optional[str], ci_dimension: str
) -> Dict[str, Any]:
    async with _ollama_semaphore:
        chunks = await retrieve(query, competitor=competitor, ci_dimension_filter=ci_dimension)
        if not chunks:
            logger.warning(f"No chunks retrieved for sub-query: {query[:60]}")
            return {
                "summary": "Insufficient public data available for this dimension.",
                "key_metrics": [], "citations": [], "confidence_score": 0.0,
            }
        return await generate_answer_async(query, chunks, competitor or "all", ci_dimension)



async def compare_competitors(
    ci_dimension: str,
    query: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Generate CI answers for all 5 competitors for one dimension, concurrently.
    """
    effective_query = query or f"Provide a comprehensive analysis of {ci_dimension} for this competitor"
    cache_key = f"compare::{ci_dimension}"

    if use_cache:
        cached = await cache_get(effective_query, cache_key)
        if cached:
            return cached

    tasks = {
        comp: _retrieve_and_generate(
            effective_query.format(competitor=comp.replace("_", " ").title()),
            comp,
            ci_dimension,
        )
        for comp in settings.COMPETITORS
    }

    results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
    comparison = {}
    for comp, result in zip(tasks.keys(), results_list):
        if isinstance(result, dict):
            comparison[comp] = result
        else:
            comparison[comp] = {"summary": "Error retrieving data", "confidence_score": 0.0}

    output = {
        "ci_dimension": ci_dimension,
        "generated_at": date.today().isoformat(),
        "competitors": comparison,
    }

    if use_cache:
        await cache_set(effective_query, output, cache_key)

    return output


async def full_competitor_report(
    competitor: str,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Generate complete CI report for one competitor across all dimensions.
    """
    cache_key = f"report::{competitor}"
    dummy_query = f"full report {competitor}"

    if use_cache:
        cached = await cache_get(dummy_query, cache_key)
        if cached:
            return cached

    tasks = {}
    for dim in settings.CI_DIMENSIONS:
        q = f"Provide a comprehensive analysis of {dim.replace('_',' ')} for {competitor.replace('_',' ').title()}"
        tasks[dim] = _retrieve_and_generate(q, competitor, dim)

    results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
    dimensions = {}
    for dim, result in zip(tasks.keys(), results_list):
        dimensions[dim] = result if isinstance(result, dict) else {
            "summary": "Error", "confidence_score": 0.0
        }

    report = {
        "competitor": competitor,
        "competitor_display": competitor.replace("_", " ").title(),
        "generated_at": date.today().isoformat(),
        "dimensions": dimensions,
        "overall_confidence": _avg_confidence(dimensions),
    }

    if use_cache:
        await cache_set(dummy_query, report, cache_key)

    return report


# ─── Helpers ─────────────────────────────────────────────────────
def _merge_results(results: List[Dict[str, Any]], original_query: str) -> Dict[str, Any]:
    """Merge multiple sub-query results into a single response."""
    all_metrics = []
    all_citations = []
    summaries = []
    scores = []

    for r in results:
        if r.get("summary"):
            summaries.append(r["summary"])
        all_metrics.extend(r.get("key_metrics", []))
        all_citations.extend(r.get("citations", []))
        if r.get("confidence_score") is not None:
            scores.append(r["confidence_score"])

    # Deduplicate citations by source+date
    seen = set()
    unique_citations = []
    for c in all_citations:
        key = (c.get("source"), c.get("date"))
        if key not in seen:
            seen.add(key)
            unique_citations.append(c)

    return {
        "query": original_query,
        "summary": " ".join(summaries[:3]),   # top 3 summaries
        "key_metrics": all_metrics[:20],
        "citations": unique_citations[:15],
        "confidence_score": sum(scores) / len(scores) if scores else 0.0,
        "sub_query_count": len(results),
    }


def _avg_confidence(dimensions: Dict[str, Any]) -> float:
    scores = [v.get("confidence_score", 0) for v in dimensions.values() if isinstance(v, dict)]
    return round(sum(scores) / len(scores), 2) if scores else 0.0

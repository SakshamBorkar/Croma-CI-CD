"""
app/rag/generator.py
─────────────────────
LLM answer generation using Ollama.

Features:
  - Structured JSON output (summary, key_metrics, citations, confidence_score)
  - Per-dimension prompt templates (from spec Layer 4b)
  - Hallucination guard: verifies citations exist in retrieved context
  - Runs 100% locally via Ollama (mistral / llama3 / llama3.1)

Run before starting:
    ollama pull mistral
"""

import json
import re
from typing import Any, Dict, List, Optional

import ollama
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

# ─── Prompt templates per CI dimension ───────────────────────────
SYSTEM_PROMPT = """You are a competitive intelligence analyst specialising in Indian electronics retail.
You will be given excerpts from publicly available documents about: {competitor_display}.
Answer ONLY from the provided context. For every factual claim, cite the source document name and date in brackets.
If the context does not contain sufficient information, state: "Insufficient public data available for this dimension."

Return ONLY a valid JSON object with these keys:
{{
  "summary": "<2-4 sentence executive summary>",
  "key_metrics": [
    {{"metric": "<name>", "value": "<value>", "period": "<year/quarter>"}}
  ],
  "citations": [
    {{"source": "<document name or URL>", "date": "<YYYY-MM-DD>", "excerpt": "<15-word relevant excerpt>"}}
  ],
  "confidence_score": <float 0.0 to 1.0>
}}

Do not include any text outside the JSON object."""

DIMENSION_CONTEXT = {
    "business_model": "Focus on: channels, product portfolio, customer segments, marketing, EMI/BNPL, after-sales, supply chain, technology usage.",
    "geographical_presence": "Focus on: store count by city/state, new store openings, expansion plans, store formats, ownership model.",
    "financial_performance": "Focus on: revenue trends, EBITDA margins, PAT, unit economics, credit ratings, debt profile.",
    "customer_feedback": "Focus on: NPS indicators, Google/App Store ratings, common complaint themes, praise patterns.",
    "strategic_initiatives": "Focus on: investments, acquisitions, leadership changes, technology partnerships, sustainability/ESG.",
    "future_outlook": "Focus on: published guidance, management commentary, analyst forecasts, expansion announcements.",
}

USER_PROMPT_TEMPLATE = """CI Dimension: {dimension}
{dimension_context}

Competitor: {competitor_display}

Retrieved context documents:
---
{context}
---

Question: {query}

Respond with the JSON object only."""


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=10))
def generate_answer(
    query: str,
    context_chunks: List[Dict[str, Any]],
    competitor: str,
    ci_dimension: str = "general",
) -> Dict[str, Any]:
    """
    Generate a structured CI answer using Ollama.

    Args:
        query: original or sub-query string
        context_chunks: list of retrieved chunk dicts (text + metadata)
        competitor: e.g. "vijay_sales"
        ci_dimension: e.g. "financial_performance"

    Returns:
        Structured dict: {summary, key_metrics, citations, confidence_score}
    """
    competitor_display = competitor.replace("_", " ").title()

    # Build context string from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source_url", "Unknown source")
        pub_date = meta.get("publication_date", "Unknown date")
        context_parts.append(
            f"[{i}] Source: {source} | Date: {pub_date}\n{chunk['text']}"
        )
    context_str = "\n\n".join(context_parts)

    system_msg = SYSTEM_PROMPT.format(competitor_display=competitor_display)
    user_msg = USER_PROMPT_TEMPLATE.format(
        dimension=ci_dimension,
        dimension_context=DIMENSION_CONTEXT.get(ci_dimension, ""),
        competitor_display=competitor_display,
        context=context_str[:12000],  # context window guard
        query=query,
    )

    try:
        response = ollama.chat(
            model=settings.OLLAMA_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            options={
                "temperature": settings.OLLAMA_TEMPERATURE,
                "num_predict": settings.OLLAMA_MAX_TOKENS,
            },
        )

        raw_text = response["message"]["content"].strip()
        result = _parse_json_response(raw_text)
        result = _hallucination_guard(result, context_chunks)
        result["competitor"] = competitor
        result["ci_dimension"] = ci_dimension
        result["query"] = query
        return result

    except Exception as e:
        logger.error(f"LLM generation failed for {competitor}/{ci_dimension}: {e}")
        return _empty_response(competitor, ci_dimension, query, error=str(e))


async def generate_answer_async(
    query: str,
    context_chunks: List[Dict[str, Any]],
    competitor: str,
    ci_dimension: str = "general",
) -> Dict[str, Any]:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_answer, query, context_chunks, competitor, ci_dimension)


# ─── JSON parser with fallback ────────────────────────────────────
def _parse_json_response(raw: str) -> Dict[str, Any]:
    """Extract JSON from LLM output — handle markdown code fences."""
    # Strip markdown fences
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()

    # Find first { ... }
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse LLM JSON response; returning raw in summary")
    return {
        "summary": raw[:500],
        "key_metrics": [],
        "citations": [],
        "confidence_score": 0.1,
    }


# ─── Hallucination guard ──────────────────────────────────────────
def _hallucination_guard(result: Dict[str, Any], context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Remove citations whose source URLs don't appear in retrieved context.
    Reduces confidence_score if many citations are removed.
    """
    valid_sources = set()
    for chunk in context_chunks:
        meta = chunk.get("metadata", {})
        url = meta.get("source_url", "")
        if url:
            valid_sources.add(url)
            # also add domain
            from urllib.parse import urlparse
            valid_sources.add(urlparse(url).netloc)

    citations = result.get("citations", [])
    valid_citations = []
    for cit in citations:
        src = cit.get("source", "")
        # Accept if source is in valid_sources or is a generic descriptor
        if any(vs in src or src in vs for vs in valid_sources) or len(src) < 30:
            valid_citations.append(cit)
        else:
            logger.debug(f"Hallucination guard: removed citation {src}")

    removed = len(citations) - len(valid_citations)
    if removed > 0:
        penalty = min(0.3, removed * 0.1)
        result["confidence_score"] = max(0.0, result.get("confidence_score", 0.5) - penalty)

    result["citations"] = valid_citations
    return result


def _empty_response(competitor, ci_dimension, query, error="") -> Dict[str, Any]:
    return {
        "summary": f"Insufficient public data available for this dimension. Error: {error}",
        "key_metrics": [],
        "citations": [],
        "confidence_score": 0.0,
        "competitor": competitor,
        "ci_dimension": ci_dimension,
        "query": query,
    }

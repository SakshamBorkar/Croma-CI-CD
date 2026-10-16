"""
app/rag/pipeline.py (LangGraph Delegation Wrapper)
──────────────────────────────────────────────────
Full RAG pipeline orchestrator delegating to LangGraph multi-agent workflow.

Exposes:
  - run_query: natural language query across agents
  - compare_competitors: compare all competitors for one dimension
  - full_competitor_report: generate all dimensions for one competitor
"""
import asyncio
from datetime import date
from typing import Any, Dict, List, Optional

from loguru import logger

from app.agents.orchestrator import ci_graph
from app.agents.state import CIPipelineState
from app.core.cache import cache_get, cache_set
from app.core.config import settings


async def run_query(
    query: str,
    competitor: Optional[str] = None,
    ci_dimension: Optional[str] = None,
    use_cache: bool = True,
    selected_mode: str = "auto",
    source_scope: str = "all_sources",
    selected_document_ids: Optional[List[str]] = None,
    user_id: Optional[str] = "demo_user",
) -> Dict[str, Any]:
    """
    Main entry point: free-form NL query with user-controlled agent mode and document scoping.
    Executes through the dynamic LangGraph multi-agent workflow.
    """
    doc_ids_key = ",".join(sorted(selected_document_ids or []))
    cache_key_extra = f"{competitor or 'all'}::{ci_dimension or 'all'}::{selected_mode}::{source_scope}::{doc_ids_key}"
    if use_cache:
        cached = await cache_get(query, cache_key_extra)
        if cached:
            return cached

    initial_state: CIPipelineState = {
        "query": query,
        "competitor": competitor,
        "ci_dimension": ci_dimension,
        "use_cache": use_cache,
        "user_id": user_id or "demo_user",
        "selected_mode": selected_mode,
        "source_scope": source_scope,
        "selected_document_ids": selected_document_ids or [],
        "document_processing_status": {},
        "uploaded_document_references": [],
        "needs_web_research": selected_mode == "research" or (selected_mode == "auto"),
        "needs_rag_retrieval": True,
        "selected_agents": [],
        "plan_rationale": "",
        "current_agent": "init",
        "iteration_count": 0,
        "web_findings": [],
        "knowledge_base_chunks": [],
        "retrieved_document_chunks": [],
        "raw_insights": [],
        "nl_synthesis": None,
        "validation_issues": [],
        "missing_information": [],
        "conflicts": [],
        "final_report": {},
        "errors": [],
    }

    result = await ci_graph.ainvoke(initial_state)
    report = result.get("final_report", {})
    insights = list(report.get("competitors", {}).values())

    # Build comprehensive metrics and citations
    metrics = [m for i in insights for m in i.get("key_metrics", [])][:20]
    citations = report.get("citations", []) or [c for i in insights for c in i.get("citations", [])][:15]

    response = {
        "query": query,
        "selected_mode": selected_mode,
        "selected_agents": report.get("selected_agents", []),
        "plan_rationale": report.get("plan_rationale", ""),
        "source_scope": source_scope,
        "primary_agent": report.get("primary_agent", "LangGraph Orchestrator"),
        "summary": report.get("summary") or " ".join(i.get("summary", "") for i in insights[:3]),
        "key_metrics": metrics,
        "citations": citations,
        "confidence_score": report.get("overall_confidence", 0.0),
        "sub_query_count": len(insights),
        "competitors": report.get("competitors", {}),
        "validation_summary": report.get("validation_summary", {}),
        "missing_information": report.get("missing_information", []),
        "conflicts": report.get("conflicts", []),
        "agent_traces": {
            "selected_mode": selected_mode,
            "selected_agents": report.get("selected_agents", []),
            "plan_rationale": report.get("plan_rationale", ""),
            "source_scope": source_scope,
            "primary_agent": report.get("primary_agent", "LangGraph Orchestrator"),
            "research_agent": {
                "active": len(result.get("web_findings", [])) > 0 or selected_mode == "research",
                "findings_count": len(result.get("web_findings", [])),
                "findings": result.get("web_findings", [])[:6],
            },
            "rag_agent": {
                "active": len(result.get("knowledge_base_chunks", [])) > 0 or selected_mode == "rag",
                "chunks_count": len(result.get("knowledge_base_chunks", [])),
                "uploaded_chunks_count": len(result.get("retrieved_document_chunks", [])),
            },
            "analysis_agent": {
                "active": len(result.get("raw_insights", [])) > 0 or selected_mode == "analysis",
                "competitors_analyzed": len(insights),
            },
            "validation_agent": {
                "active": len(result.get("validation_issues", [])) > 0 or selected_mode in ("validation", "auto"),
                "issues_count": len(result.get("validation_issues", [])),
                "confidence_score": report.get("overall_confidence", 0.0),
            },
        },
    }

    if use_cache:
        await cache_set(query, response, cache_key_extra)
    return response


async def compare_competitors(
    ci_dimension: str,
    query: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Compare all 5 competitors on a single dimension via the LangGraph workflow.
    """
    effective_query = query or f"Provide a comprehensive analysis of {ci_dimension}"
    cache_key = f"compare::{ci_dimension}"

    if use_cache:
        cached = await cache_get(effective_query, cache_key)
        if cached:
            return cached

    initial_state: CIPipelineState = {
        "query": effective_query,
        "competitor": None,
        "ci_dimension": ci_dimension,
        "use_cache": False,
        "needs_web_research": True,
        "current_agent": "init",
        "iteration_count": 0,
        "web_findings": [],
        "knowledge_base_chunks": [],
        "raw_insights": [],
        "validation_issues": [],
        "final_report": {},
        "errors": [],
    }

    result = await ci_graph.ainvoke(initial_state)
    report = result.get("final_report", {})

    output = {
        "ci_dimension": ci_dimension,
        "generated_at": date.today().isoformat(),
        "competitors": report.get("competitors", {}),
        "overall_confidence": report.get("overall_confidence", 0.0),
    }

    if use_cache:
        await cache_set(effective_query, output, cache_key)
    return output


async def full_competitor_report(
    competitor: str,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Generate complete CI report for one competitor across all dimensions using LangGraph.
    """
    cache_key = f"report::{competitor}"
    dummy_query = f"full report {competitor}"

    if use_cache:
        cached = await cache_get(dummy_query, cache_key)
        if cached:
            return cached

    tasks = {}
    for dim in settings.CI_DIMENSIONS:
        q = f"Provide a comprehensive analysis of {dim.replace('_', ' ')} for {competitor.replace('_', ' ').title()}"
        initial_state: CIPipelineState = {
            "query": q,
            "competitor": competitor,
            "ci_dimension": dim,
            "use_cache": False,
            "needs_web_research": False,
            "current_agent": "init",
            "iteration_count": 0,
            "web_findings": [],
            "knowledge_base_chunks": [],
            "raw_insights": [],
            "validation_issues": [],
            "final_report": {},
            "errors": [],
        }
        tasks[dim] = ci_graph.ainvoke(initial_state)

    results_list = await asyncio.gather(*tasks.values(), return_exceptions=True)
    dimensions = {}
    for dim, res in zip(tasks.keys(), results_list):
        if isinstance(res, dict):
            report = res.get("final_report", {})
            insights = report.get("competitors", {})
            comp_insight = insights.get(competitor, {})
            dimensions[dim] = comp_insight or {
                "summary": "Insufficient public data available for this dimension.",
                "confidence_score": 0.0,
            }
        else:
            logger.error(f"Error evaluating dimension {dim} for {competitor}: {res}")
            dimensions[dim] = {"summary": "Error generating dimension data", "confidence_score": 0.0}

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


def _avg_confidence(dimensions: Dict[str, Any]) -> float:
    scores = [v.get("confidence_score", 0) for v in dimensions.values() if isinstance(v, dict)]
    return round(sum(scores) / len(scores), 2) if scores else 0.0

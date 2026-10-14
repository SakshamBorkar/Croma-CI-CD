"""
app/agents/analysis_agent.py
Analysis Agent: Synthesizes knowledge-base documents and web findings using Ollama LLM.
"""
from typing import Dict, Any, List
from loguru import logger
from app.agents.state import CIPipelineState, CompetitorInsight
from app.rag.generator import generate_answer_async
from app.core.config import settings


async def run_analysis_agent(state: CIPipelineState) -> Dict[str, Any]:
    query = state["query"]
    dimension = state.get("ci_dimension") or "general"
    target_competitors = (
        [state["competitor"]] if state.get("competitor") else settings.COMPETITORS
    )

    kb_chunks = state.get("knowledge_base_chunks", [])
    web_findings = state.get("web_findings", [])

    insights: List[CompetitorInsight] = []
    logger.info(f"[Analysis Agent] Generating synthesis for {target_competitors}...")

    for comp in target_competitors:
        comp_context = [c for c in kb_chunks if c["metadata"].get("competitor") == comp]

        for w in web_findings:
            if w["competitor"] == comp:
                comp_context.append({
                    "id": f"web_{w['url'][:20]}",
                    "text": f"{w['title']}: {w['snippet']}",
                    "metadata": {"source_url": w["url"], "publication_date": "Recent"}
                })

        if not comp_context:
            insights.append(CompetitorInsight(
                competitor=comp,
                ci_dimension=dimension,
                summary="Insufficient public data available for this dimension.",
                key_metrics=[],
                citations=[],
                confidence_score=0.0
            ))
            continue

        raw = await generate_answer_async(
            query=query,
            context_chunks=comp_context,
            competitor=comp,
            ci_dimension=dimension
        )

        insights.append(CompetitorInsight(
            competitor=comp,
            ci_dimension=dimension,
            summary=raw.get("summary", ""),
            key_metrics=raw.get("key_metrics", []),
            citations=raw.get("citations", []),
            confidence_score=raw.get("confidence_score", 0.0)
        ))

    return {
        "raw_insights": insights,
        "current_agent": "analysis_agent"
    }

"""
app/agents/analysis_agent.py
────────────────────────────
Analysis Agent: Analyzes competitor data and documents.
Produces comparisons, pricing tables, trends, insights, and recommendations.
Uses available evidence from knowledge base, uploaded documents, and web research.
If required data is unavailable, clearly identifies the missing information.
"""
from typing import Dict, Any, List
from loguru import logger
from app.agents.state import CIPipelineState, CompetitorInsight
from app.rag.generator import generate_answer_async, generate_synthesis_async
from app.core.config import settings


async def run_analysis_agent(state: CIPipelineState) -> Dict[str, Any]:
    query = state["query"]
    dimension = state.get("ci_dimension") or "general"
    target_competitors = (
        [state["competitor"]] if state.get("competitor") else settings.COMPETITORS
    )

    kb_chunks = state.get("knowledge_base_chunks", [])
    doc_chunks = state.get("retrieved_document_chunks", [])
    web_findings = state.get("web_findings", [])
    missing_info: List[str] = list(state.get("missing_information", []))

    insights: List[CompetitorInsight] = []
    logger.info(f"[Analysis Agent] Synthesizing evidence for {target_competitors}...")

    # Build context for each competitor
    for comp in target_competitors:
        comp_context = [c for c in kb_chunks if c["metadata"].get("competitor") == comp]

        # Add relevant uploaded document chunks
        for u in doc_chunks:
            u_text = u["text"]
            citation = u.get("metadata", {}).get("citation_label") or f"[{u.get('metadata', {}).get('filename', 'Doc')}]"
            # Include if mentions competitor or if general query
            if comp.replace("_", " ").lower() in u_text.lower() or not state.get("competitor") or len(doc_chunks) <= 4:
                comp_context.append({
                    "id": u["id"],
                    "text": u_text,
                    "metadata": {
                        "source_url": citation,
                        "publication_date": "Uploaded Document",
                        "citation_label": citation,
                    }
                })

        # Add web findings
        for w in web_findings:
            if w.get("competitor") == comp:
                comp_context.append({
                    "id": f"web_{w['url'][:20]}",
                    "text": f"{w['title']}: {w['snippet']}",
                    "metadata": {"source_url": w["url"], "publication_date": "Recent Web Hit"}
                })

        if not comp_context:
            note = f"Missing data for {comp.replace('_', ' ').title()}: No verified evidence found in knowledge base or uploaded documents."
            if note not in missing_info:
                missing_info.append(note)
            insights.append(CompetitorInsight(
                competitor=comp,
                ci_dimension=dimension,
                summary=f"Insufficient verified data available for {comp.replace('_', ' ').title()} on dimension '{dimension}'.",
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

    # Generate overarching Natural Language synthesis across all retrieved evidence
    all_context = kb_chunks + doc_chunks
    for w in web_findings:
        all_context.append({
            "id": f"web_{w['url'][:20]}",
            "text": f"{w['title']}: {w['snippet']}",
            "metadata": {"source_url": w["url"], "competitor": w.get("competitor", "")}
        })

    nl_synthesis = await generate_synthesis_async(query, [dict(i) for i in insights], all_context)

    return {
        "raw_insights": insights,
        "nl_synthesis": nl_synthesis,
        "missing_information": missing_info,
        "current_agent": "analysis_agent"
    }

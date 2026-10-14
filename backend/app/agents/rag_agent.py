"""
app/agents/rag_agent.py
RAG Agent: Performs hybrid vector retrieval (ChromaDB) and BM25 sparse re-ranking.
"""
from typing import Dict, Any, List
from loguru import logger
from app.agents.state import CIPipelineState, RetrievedChunk
from app.rag.retriever import retrieve
from app.core.config import settings


async def run_rag_agent(state: CIPipelineState) -> Dict[str, Any]:
    query = state["query"]
    target_competitors = (
        [state["competitor"]] if state.get("competitor") else settings.COMPETITORS
    )
    dimension = state.get("ci_dimension")

    all_chunks: List[RetrievedChunk] = []
    logger.info(f"[RAG Agent] Retrieving internal documents for {target_competitors}...")

    for comp in target_competitors:
        chunks = await retrieve(
            query=query,
            competitor=comp,
            ci_dimension_filter=dimension,
            top_k_final=settings.TOP_K_RERANK,
        )
        for c in chunks:
            all_chunks.append(RetrievedChunk(
                id=c["id"],
                text=c["text"],
                score=c.get("rrf_score", c.get("score", 0.0)),
                metadata=c["metadata"]
            ))

    return {
        "knowledge_base_chunks": all_chunks,
        "current_agent": "rag_agent"
    }

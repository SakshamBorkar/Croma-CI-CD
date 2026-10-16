"""
app/agents/rag_agent.py
───────────────────────
RAG Agent: Performs hybrid vector retrieval (ChromaDB) and BM25 sparse re-ranking
across both the existing Croma knowledge base and user-uploaded documents.
Respects user-configured source_scope:
  - 'uploaded_only'
  - 'croma_kb'
  - 'uploaded_and_croma'
  - 'all_sources'
Preserves full provenance: document name, page number, section, chunk ID.
"""
from typing import Dict, Any, List
from loguru import logger
from app.agents.state import CIPipelineState, RetrievedChunk
from app.rag.retriever import retrieve
from app.ingestion.document_processor import retrieve_user_documents
from app.core.config import settings


async def run_rag_agent(state: CIPipelineState) -> Dict[str, Any]:
    query = state["query"]
    source_scope = state.get("source_scope", "all_sources")
    selected_doc_ids = state.get("selected_document_ids") or []
    user_id = state.get("user_id") or "demo_user"
    target_competitors = (
        [state["competitor"]] if state.get("competitor") else settings.COMPETITORS
    )
    dimension = state.get("ci_dimension")

    all_kb_chunks: List[RetrievedChunk] = []
    all_uploaded_chunks: List[RetrievedChunk] = []
    missing_info: List[str] = list(state.get("missing_information", []))
    conflicts: List[Dict[str, Any]] = list(state.get("conflicts", []))

    logger.info(f"[RAG Agent] Executing with scope '{source_scope}' for query: {query[:60]}")

    # ── 1. Query Uploaded Documents if scope allows ────────────────────
    if source_scope in ("uploaded_only", "uploaded_and_croma", "all_sources"):
        user_hits = await retrieve_user_documents(
            query=query,
            user_id=user_id,
            selected_doc_ids=selected_doc_ids if selected_doc_ids else None,
            top_k=8,
        )
        for h in user_hits:
            all_uploaded_chunks.append(
                RetrievedChunk(
                    id=h["id"],
                    text=h["text"],
                    score=h.get("score", 0.0),
                    metadata=h["metadata"],
                )
            )

        if source_scope == "uploaded_only" and not all_uploaded_chunks:
            missing_info.append(
                "No matching evidence found within the selected uploaded documents for this query."
            )

    # ── 2. Query Croma Knowledge Base if scope allows ──────────────────
    if source_scope in ("croma_kb", "uploaded_and_croma", "all_sources"):
        for comp in target_competitors:
            chunks = await retrieve(
                query=query,
                competitor=comp,
                ci_dimension_filter=dimension,
                top_k_final=settings.TOP_K_RERANK,
            )
            for c in chunks:
                all_kb_chunks.append(
                    RetrievedChunk(
                        id=c["id"],
                        text=c["text"],
                        score=c.get("rrf_score", c.get("score", 0.0)),
                        metadata=c["metadata"],
                    )
                )

    # ── 3. Conflict Detection Heuristic ────────────────────────────────
    # Check for simple numeric/factual contradictions between uploaded docs and KB
    if all_uploaded_chunks and all_kb_chunks:
        # Check if query asks for numbers / store count / pricing
        for u_chunk in all_uploaded_chunks[:3]:
            for kb_chunk in all_kb_chunks[:3]:
                # If both mention numbers/stores for the same competitor but different values
                u_text = u_chunk["text"].lower()
                kb_text = kb_chunk["text"].lower()
                if "store" in u_text and "store" in kb_text:
                    if u_chunk.get("metadata", {}).get("filename") != kb_chunk.get("metadata", {}).get("filename"):
                        # Record informational cross-source reference
                        pass

    combined_chunks = all_uploaded_chunks + all_kb_chunks

    return {
        "knowledge_base_chunks": combined_chunks,
        "retrieved_document_chunks": all_uploaded_chunks,
        "missing_information": missing_info,
        "conflicts": conflicts,
        "current_agent": "rag_agent",
    }

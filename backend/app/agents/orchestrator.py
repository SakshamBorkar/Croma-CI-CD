"""
app/agents/orchestrator.py
──────────────────────────
LangGraph Orchestrator with User-Selectable Agent Modes:
  - Option A: Auto Mode (default) — Dynamic multi-agent coordination.
  - Option B: Research Agent — Web crawling & competitor announcements.
  - Option C: RAG Agent — Hybrid retrieval across Croma KB & uploaded documents.
  - Option D: Analysis Agent — Synthesize comparisons, pricing, trends, and missing info.
  - Option E: Validation Agent — Audit claims, detect conflicts, calibrate confidence.

Single-agent selection executes that agent as primary task and respects user choice.
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.agents.state import CIPipelineState
from app.agents.research_agent import run_research_agent
from app.agents.rag_agent import run_rag_agent
from app.agents.analysis_agent import run_analysis_agent
from app.agents.validation_agent import run_validation_agent


def orchestrator_plan(state: CIPipelineState) -> Dict[str, Any]:
    """
    Planning node: Inspects the user's natural language query and dynamically
    selects which specialized agents need to execute.
    """
    query = state["query"].lower()
    mode = state.get("selected_mode", "auto")

    # 1. Dynamic intent analysis on user query
    web_triggers = [
        "price", "pricing", "recent", "latest", "expansion", "offer", "discount",
        "launch", "announced", "news", "trend", "today", "current", "update"
    ]
    rag_triggers = [
        "store", "stores", "revenue", "ebitda", "financial", "margin", "crore",
        "pat", "footprint", "presence", "business model", "competitor", "reliance",
        "vijay", "aditya", "poojara", "bajaj", "document", "report", "filing", "compare"
    ]

    has_web_intent = any(w in query for w in web_triggers)
    has_rag_intent = any(w in query for w in rag_triggers) or not has_web_intent

    selected_agents: List[str] = []
    plan_steps: List[str] = []

    if mode == "auto":
        if has_web_intent:
            selected_agents.append("research_agent")
            plan_steps.append("Research Agent (Live web search for latest pricing, offers, and store moves)")
        
        # Always include RAG agent if competitor/financial/store data is queried or uploaded docs are selected
        if has_rag_intent or state.get("selected_document_ids"):
            selected_agents.append("rag_agent")
            plan_steps.append("RAG Agent (Hybrid retrieval across ChromaDB knowledge base & documents)")

        # Analysis agent is always selected to formulate a coherent Natural Language synthesized answer
        selected_agents.append("analysis_agent")
        plan_steps.append("Analysis Agent (Cross-competitor synthesis & Natural Language generation)")

        # Validation agent verifies citations and checks for hallucinations
        selected_agents.append("validation_agent")
        plan_steps.append("Validation Agent (Fact verification & citation auditing)")

    else:
        # User specified override mode
        if mode == "research":
            selected_agents = ["research_agent", "analysis_agent", "validation_agent"]
            plan_steps = ["Research Agent (Primary)", "Analysis Agent", "Validation Agent"]
        elif mode == "rag":
            selected_agents = ["rag_agent", "analysis_agent", "validation_agent"]
            plan_steps = ["RAG Agent (Primary)", "Analysis Agent", "Validation Agent"]
        elif mode == "analysis":
            selected_agents = ["rag_agent", "analysis_agent", "validation_agent"]
            plan_steps = ["RAG Agent", "Analysis Agent (Primary)", "Validation Agent"]
        elif mode == "validation":
            selected_agents = ["rag_agent", "analysis_agent", "validation_agent"]
            plan_steps = ["RAG Agent", "Analysis Agent", "Validation Agent (Primary Audit)"]

    rationale = f"Orchestrator analyzed query \"{state['query']}\" and dynamically activated: {', '.join(selected_agents)}."

    return {
        "needs_web_research": "research_agent" in selected_agents,
        "needs_rag_retrieval": "rag_agent" in selected_agents,
        "selected_agents": selected_agents,
        "plan_rationale": rationale,
        "selected_mode": mode,
        "current_agent": "orchestrator",
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def orchestrator_finalize(state: CIPipelineState) -> Dict[str, Any]:
    """
    Assembles the final report. Always returns a rich, Natural Language synthesized
    answer based on the retrieved evidence, key verified metrics, and citation audits.
    """
    mode = state.get("selected_mode", "auto")
    scope = state.get("source_scope", "all_sources")
    insights = state.get("raw_insights", [])
    issues = state.get("validation_issues", [])
    web_findings = state.get("web_findings", [])
    doc_chunks = state.get("retrieved_document_chunks", [])
    kb_chunks = state.get("knowledge_base_chunks", [])
    missing_info = state.get("missing_information", [])
    conflicts = state.get("conflicts", [])
    selected_agents = state.get("selected_agents", ["orchestrator", "rag_agent", "analysis_agent"])
    plan_rationale = state.get("plan_rationale", "")

    competitors_dict = {ins["competitor"]: ins for ins in insights}

    # ── Requirement 2: Natural Language Answer based on retrieved chunks ──
    # Priority:
    # 1. nl_synthesis generated by analysis_agent based on all chunks
    # 2. Rich markdown synthesis of competitor summaries
    # 3. Fallback direct explanation
    if state.get("nl_synthesis") and len(state["nl_synthesis"].strip()) > 30:
        summary = state["nl_synthesis"].strip()
    else:
        # Formulate articulate NL answer from available insights
        valid_summaries = [
            f"**{ins['competitor'].replace('_', ' ').title()}**: {ins['summary']}"
            for ins in insights
            if ins.get("summary") and "Insufficient" not in ins["summary"]
        ]
        if valid_summaries:
            summary = "\n\n".join(valid_summaries)
        else:
            summary = "Based on the retrieved intelligence chunks, insufficient verified evidence was found for the requested criteria."

    # Collect citations and deduplicate
    citations = []
    seen_sources = set()
    for ins in insights:
        for c in ins.get("citations", []):
            key = (c.get("source"), c.get("excerpt", "")[:40])
            if key not in seen_sources:
                seen_sources.add(key)
                citations.append(c)

    # In case citations weren't produced, harvest from retrieved chunks
    if not citations and (kb_chunks or doc_chunks):
        all_chunks = doc_chunks + kb_chunks
        for c in all_chunks[:10]:
            meta = c.get("metadata", {})
            src = meta.get("citation_label") or meta.get("source_url") or meta.get("source_title") or "Croma Knowledge Base"
            citations.append({
                "source": src,
                "date": str(meta.get("publication_date", "Document")),
                "excerpt": c["text"][:140] + "...",
            })

    # Confidence calculation
    avg_conf = (sum(i["confidence_score"] for i in insights) / len(insights)) if insights else 0.8
    failed_checks = len([i for i in issues if not i.get("passed", False)])
    overall_confidence = max(0.1, round(avg_conf - (failed_checks * 0.05), 2))

    report = {
        "query": state["query"],
        "ci_dimension": state.get("ci_dimension"),
        "selected_mode": mode,
        "selected_agents": selected_agents,
        "plan_rationale": plan_rationale,
        "source_scope": scope,
        "primary_agent": "LangGraph Orchestrator",
        "summary": summary,
        "competitors": competitors_dict,
        "citations": citations[:20],
        "overall_confidence": overall_confidence,
        "missing_information": missing_info,
        "conflicts": conflicts,
        "validation_summary": {
            "total_checks": len(issues) + len(citations),
            "passed": failed_checks == 0,
            "issues": issues,
        },
        "retrieved_document_count": len(doc_chunks),
        "web_findings_count": len(web_findings),
    }

    return {"final_report": report, "current_agent": "report"}


# ── Routing Functions ───────────────────────────────────────────────
def route_orchestrator(
    state: CIPipelineState,
) -> Literal["research_agent", "rag_agent", "analysis_agent"]:
    selected = state.get("selected_agents", [])
    if "research_agent" in selected:
        return "research_agent"
    if "rag_agent" in selected:
        return "rag_agent"
    return "analysis_agent"


route_planning_edge = route_orchestrator


def route_after_research(
    state: CIPipelineState,
) -> Literal["rag_agent", "analysis_agent"]:
    selected = state.get("selected_agents", [])
    if "rag_agent" in selected:
        return "rag_agent"
    return "analysis_agent"


def route_after_rag(
    state: CIPipelineState,
) -> Literal["analysis_agent"]:
    # Always route retrieved chunks to analysis agent to produce a rich Natural Language answer
    return "analysis_agent"


def route_after_analysis(
    state: CIPipelineState,
) -> Literal["validation_agent", "report_assembler"]:
    selected = state.get("selected_agents", [])
    if "validation_agent" in selected:
        return "validation_agent"
    return "report_assembler"


# ── Build Graph ─────────────────────────────────────────────────────
def build_ci_orchestrator():
    builder = StateGraph(CIPipelineState)

    builder.add_node("orchestrator", orchestrator_plan)
    builder.add_node("research_agent", run_research_agent)
    builder.add_node("rag_agent", run_rag_agent)
    builder.add_node("analysis_agent", run_analysis_agent)
    builder.add_node("validation_agent", run_validation_agent)
    builder.add_node("report_assembler", orchestrator_finalize)

    builder.set_entry_point("orchestrator")

    # Conditional routing from Orchestrator
    builder.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "research_agent": "research_agent",
            "rag_agent": "rag_agent",
            "analysis_agent": "analysis_agent",
        },
    )

    # Conditional routing after Research Agent
    builder.add_conditional_edges(
        "research_agent",
        route_after_research,
        {
            "rag_agent": "rag_agent",
            "analysis_agent": "analysis_agent",
        },
    )

    # RAG Agent always feeds into Analysis Agent for Natural Language generation
    builder.add_edge("rag_agent", "analysis_agent")

    # Conditional routing after Analysis Agent
    builder.add_conditional_edges(
        "analysis_agent",
        route_after_analysis,
        {
            "validation_agent": "validation_agent",
            "report_assembler": "report_assembler",
        },
    )

    # Validation Agent always finishes at report_assembler
    builder.add_edge("validation_agent", "report_assembler")
    builder.add_edge("report_assembler", END)

    return builder.compile()


ci_graph = build_ci_orchestrator()

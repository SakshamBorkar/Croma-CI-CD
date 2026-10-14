"""
app/agents/orchestrator.py
LangGraph Orchestrator: Directs task flow, routes conditionally, and outputs final report.
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from app.agents.state import CIPipelineState
from app.agents.research_agent import run_research_agent
from app.agents.rag_agent import run_rag_agent
from app.agents.analysis_agent import run_analysis_agent
from app.agents.validation_agent import run_validation_agent


def orchestrator_plan(state: CIPipelineState) -> Dict[str, Any]:
    query = state["query"].lower()
    trigger_words = ["price", "pricing", "recent", "latest", "expansion", "offer", "discount"]
    needs_web = any(w in query for w in trigger_words)

    return {
        "needs_web_research": needs_web,
        "current_agent": "orchestrator",
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


def orchestrator_finalize(state: CIPipelineState) -> Dict[str, Any]:
    insights = state.get("raw_insights", [])
    issues = state.get("validation_issues", [])

    competitors_dict = {ins["competitor"]: ins for ins in insights}
    avg_confidence = (
        sum(ins["confidence_score"] for ins in insights) / len(insights)
        if insights else 0.0
    )

    report = {
        "query": state["query"],
        "ci_dimension": state.get("ci_dimension"),
        "competitors": competitors_dict,
        "overall_confidence": round(avg_confidence, 2),
        "validation_summary": {
            "total_checks": len(issues) + sum(len(i["citations"]) for i in insights),
            "passed": len(issues) == 0,
            "issues": issues,
        },
    }

    return {"final_report": report, "current_agent": "report"}


def route_planning_edge(state: CIPipelineState) -> Literal["research_agent", "rag_agent"]:
    if state.get("needs_web_research"):
        return "research_agent"
    return "rag_agent"


def build_ci_orchestrator():
    builder = StateGraph(CIPipelineState)

    builder.add_node("orchestrator", orchestrator_plan)
    builder.add_node("research_agent", run_research_agent)
    builder.add_node("rag_agent", run_rag_agent)
    builder.add_node("analysis_agent", run_analysis_agent)
    builder.add_node("validation_agent", run_validation_agent)
    builder.add_node("report_assembler", orchestrator_finalize)

    builder.set_entry_point("orchestrator")

    builder.add_conditional_edges(
        "orchestrator",
        route_planning_edge,
        {
            "research_agent": "research_agent",
            "rag_agent": "rag_agent",
        },
    )

    builder.add_edge("research_agent", "rag_agent")
    builder.add_edge("rag_agent", "analysis_agent")
    builder.add_edge("analysis_agent", "validation_agent")
    builder.add_edge("validation_agent", "report_assembler")
    builder.add_edge("report_assembler", END)

    return builder.compile()


ci_graph = build_ci_orchestrator()

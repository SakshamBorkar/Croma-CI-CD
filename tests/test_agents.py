"""
tests/test_agents.py
────────────────────
Unit tests for the LangGraph multi-agent CI architecture:
- CIPipelineState schema integrity
- Orchestrator planning & routing
- Research Agent
- Validation Agent citation filtering & confidence penalty
- LangGraph compilation
"""
import pytest
from unittest.mock import patch, MagicMock

from app.agents.state import CIPipelineState, WebFinding, RetrievedChunk, CompetitorInsight
from app.agents.orchestrator import orchestrator_plan, route_planning_edge, orchestrator_finalize, ci_graph
from app.agents.validation_agent import run_validation_agent
from app.agents.research_agent import run_research_agent


class TestAgentStateAndPlanning:
    def test_orchestrator_detects_web_trigger_words(self):
        state: CIPipelineState = {
            "query": "What are the latest pricing discounts for Vijay Sales?",
            "competitor": "vijay_sales",
            "ci_dimension": "financial_performance",
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
        res = orchestrator_plan(state)
        assert res["needs_web_research"] is True
        assert res["iteration_count"] == 1

        route = route_planning_edge({**state, **res})
        assert route == "research_agent"

    def test_orchestrator_routes_to_rag_when_no_web_needed(self):
        state: CIPipelineState = {
            "query": "Explain the business model of Reliance Digital",
            "competitor": "reliance_digital",
            "ci_dimension": "business_model",
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
        res = orchestrator_plan(state)
        assert res["needs_web_research"] is False
        route = route_planning_edge({**state, **res})
        assert route == "rag_agent"


class TestValidationAgent:
    def test_validation_agent_keeps_valid_and_penalizes_invalid(self):
        state: CIPipelineState = {
            "query": "store count",
            "competitor": "vijay_sales",
            "ci_dimension": "geographical_presence",
            "use_cache": False,
            "needs_web_research": False,
            "current_agent": "analysis_agent",
            "iteration_count": 1,
            "web_findings": [
                {
                    "url": "https://www.vijaysales.com/stores",
                    "title": "Stores",
                    "snippet": "120 stores in India",
                    "competitor": "vijay_sales",
                }
            ],
            "knowledge_base_chunks": [
                {
                    "id": "chunk_1",
                    "text": "Vijay Sales operates 100+ stores",
                    "score": 0.85,
                    "metadata": {
                        "source_url": "https://economictimes.indiatimes.com/news/stores",
                        "competitor": "vijay_sales",
                    },
                }
            ],
            "raw_insights": [
                {
                    "competitor": "vijay_sales",
                    "ci_dimension": "geographical_presence",
                    "summary": "Vijay Sales has widespread presence.",
                    "key_metrics": [{"metric": "Store Count", "value": "120", "period": "2024"}],
                    "citations": [
                        {
                            "source": "https://www.vijaysales.com/stores",
                            "date": "2024",
                            "excerpt": "120 stores in India",
                        },
                        {
                            "source": "https://completely-unretrieved-fake-site.com/fake-news.pdf",
                            "date": "2024",
                            "excerpt": "fabricated store numbers",
                        },
                    ],
                    "confidence_score": 0.90,
                }
            ],
            "validation_issues": [],
            "final_report": {},
            "errors": [],
        }

        result = run_validation_agent(state)
        validated_insights = result["raw_insights"]
        issues = result["validation_issues"]

        assert len(issues) == 1
        assert issues[0]["competitor"] == "vijay_sales"
        assert issues[0]["passed"] is False

        # One valid citation kept, one fake stripped
        assert len(validated_insights[0]["citations"]) == 1
        assert validated_insights[0]["citations"][0]["source"] == "https://www.vijaysales.com/stores"

        # Confidence penalized by 0.15: 0.90 - 0.15 = 0.75
        assert validated_insights[0]["confidence_score"] == 0.75


class TestLangGraphCompilation:
    def test_ci_graph_is_compiled(self):
        assert ci_graph is not None
        # Graph should have all declared agent nodes
        node_names = set(ci_graph.nodes.keys())
        expected_nodes = {
            "orchestrator",
            "research_agent",
            "rag_agent",
            "analysis_agent",
            "validation_agent",
            "report_assembler",
        }
        for node in expected_nodes:
            assert node in node_names

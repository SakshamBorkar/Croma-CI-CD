"""
app/agents/research_agent.py
Research Agent: Performs live web search & extracts dynamic competitor market updates.
"""
from typing import Dict, Any, List
from duckduckgo_search import DDGS
from loguru import logger
from app.agents.state import CIPipelineState, WebFinding
from app.core.config import settings


def run_research_agent(state: CIPipelineState) -> Dict[str, Any]:
    query = state["query"]
    target_competitors = (
        [state["competitor"]] if state.get("competitor") else settings.COMPETITORS
    )

    findings: List[WebFinding] = []
    logger.info(f"[Research Agent] Searching web for {target_competitors}...")

    for comp in target_competitors:
        comp_clean = comp.replace("_", " ").title()
        search_query = f"{comp_clean} India electronics retail {query}"
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=3))
                for r in results:
                    findings.append(WebFinding(
                        url=r.get("href", ""),
                        title=r.get("title", ""),
                        snippet=r.get("body", ""),
                        competitor=comp
                    ))
        except Exception as e:
            logger.warning(f"[Research Agent] Search query failed for {comp}: {e}")

    return {
        "web_findings": findings,
        "current_agent": "research_agent"
    }

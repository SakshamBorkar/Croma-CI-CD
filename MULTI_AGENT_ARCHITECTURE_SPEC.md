# Multi-Agent Architecture Specification & Migration Guide
**Project:** Croma Competitive Intelligence (CI) Platform  
**Target Architecture:** LangGraph Multi-Agent Orchestration (Research Agent, RAG Agent, Analysis Agent, Validation Agent)

---

## 1. Executive Summary & Reference Diagram

This specification defines the complete blueprint to transition the Croma CI platform from a linear, single-script RAG pipeline to a multi-agent orchestrated system based on **LangGraph**.

```
                               ┌────────────────┐
                               │   User Query   │
                               └───────┬────────┘
                                       │
                                       ▼
                       ┌────────────────────────────────┐
                       │    Orchestrator — LangGraph    │
                       │ Maintains state, selects tasks │
                       └───────┬───────────────┬────────┘
                               │               │
            ┌──────────────────┴──┐         ┌──┴──────────────────┐
            ▼                     ▼         ▼                     ▼
  ┌──────────────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐
  │  Research Agent  │  │ RAG Agent │  │ Analysis  │  │ Validation Agent │
  │ Web search/crawl │  │  Hybrid   │  │   Agent   │  │ Evidence/Quality │
  └──────────────────┘  └───────────┘  └───────────┘  └──────────────────┘
                               │               │
                               └───────┬───────┘
                                       │
                                       ▼
                               ┌────────────────┐
                               │  Final Report  │
                               └────────────────┘
```

---

## 2. Inventory of Required Changes

| Change Type | File Path | Purpose |
| :--- | :--- | :--- |
| **Modify** | `backend/requirements.txt` | Add `langgraph`, `duckduckgo-search` |
| **Create** | `backend/app/agents/__init__.py` | Package initializer |
| **Create** | `backend/app/agents/state.py` | Shared `TypedDict` schema across all agents |
| **Create** | `backend/app/agents/research_agent.py` | Web crawling & live internet intelligence |
| **Create** | `backend/app/agents/rag_agent.py` | ChromaDB vector search + BM25 keyword fusion |
| **Create** | `backend/app/agents/analysis_agent.py` | LLM synthesis, competitor metrics, comparisons |
| **Create** | `backend/app/agents/validation_agent.py` | Anti-hallucination checks & citation validation |
| **Create** | `backend/app/agents/orchestrator.py` | LangGraph `StateGraph` definition & routing |
| **Modify** | `backend/app/rag/pipeline.py` | Connect FastAPI endpoints to LangGraph graph |

---

## 3. Dependency Updates

### File: `backend/requirements.txt`
Add the following lines under the LangChain section:
```txt
# ── Multi-Agent Orchestration / LangGraph ──────────────────────
langgraph>=0.2.0
duckduckgo-search>=6.0.0
```

Installation command:
```powershell
backend\venv\Scripts\pip install langgraph duckduckgo-search
```

---

## 4. Full Source Code for New Modules

### File 1: `backend/app/agents/__init__.py`
```python
"""
app.agents
──────────
Multi-agent competitive intelligence architecture using LangGraph.
"""
from app.agents.orchestrator import ci_graph

__all__ = ["ci_graph"]
```

---

### File 2: `backend/app/agents/state.py`
```python
"""
app/agents/state.py
Shared TypedDict schema that flows through each node in the StateGraph.
"""
from typing import Any, Dict, List, Optional, TypedDict

class WebFinding(TypedDict):
    url: str
    title: str
    snippet: str
    competitor: str

class RetrievedChunk(TypedDict):
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]

class MetricItem(TypedDict):
    metric: str
    value: str
    period: str

class CitationItem(TypedDict):
    source: str
    date: str
    excerpt: str

class CompetitorInsight(TypedDict):
    competitor: str
    ci_dimension: str
    summary: str
    key_metrics: List[MetricItem]
    citations: List[CitationItem]
    confidence_score: float

class ValidationIssue(TypedDict):
    competitor: str
    claim: str
    reason: str
    passed: bool

class CIPipelineState(TypedDict):
    # User Input
    query: str
    competitor: Optional[str]
    ci_dimension: Optional[str]
    use_cache: bool

    # Orchestrator Decisions
    needs_web_research: bool
    current_agent: str
    iteration_count: int

    # Intermediate Agent Data
    web_findings: List[WebFinding]
    knowledge_base_chunks: List[RetrievedChunk]
    raw_insights: List[CompetitorInsight]
    validation_issues: List[ValidationIssue]

    # Final Result
    final_report: Dict[str, Any]
    errors: List[str]
```

---

### File 3: `backend/app/agents/research_agent.py`
```python
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
```

---

### File 4: `backend/app/agents/rag_agent.py`
```python
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
            top_k_final=settings.TOP_K_RERANK
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
```

---

### File 5: `backend/app/agents/analysis_agent.py`
```python
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
    dimension = state.get("ci_dimension", "general")
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
```

---

### File 6: `backend/app/agents/validation_agent.py`
```python
"""
app/agents/validation_agent.py
Validation Agent: Inspects citations, eliminates hallucinations, and calibrates confidence score.
"""
from typing import Dict, Any, List
from urllib.parse import urlparse
from app.agents.state import CIPipelineState, ValidationIssue, CompetitorInsight

def run_validation_agent(state: CIPipelineState) -> Dict[str, Any]:
    insights = state.get("raw_insights", [])
    kb_chunks = state.get("knowledge_base_chunks", [])
    web_findings = state.get("web_findings", [])

    valid_domains = set()
    for c in kb_chunks:
        url = c["metadata"].get("source_url", "")
        if url:
            valid_domains.add(urlparse(url).netloc or url)
    for w in web_findings:
        if w["url"]:
            valid_domains.add(urlparse(w["url"]).netloc or w["url"])

    validated_insights: List[CompetitorInsight] = []
    issues: List[ValidationIssue] = []

    for ins in insights:
        verified_citations = []
        comp = ins["competitor"]

        for cit in ins.get("citations", []):
            source = cit.get("source", "")
            source_domain = urlparse(source).netloc or source
            
            if any(vd in source or source in vd for vd in valid_domains) or len(source) < 30:
                verified_citations.append(cit)
            else:
                issues.append(ValidationIssue(
                    competitor=comp,
                    claim=cit.get("excerpt", ""),
                    reason=f"Citation not found in retrieved evidence: {source}",
                    passed=False
                ))

        penalty = len(ins.get("citations", [])) - len(verified_citations)
        adjusted_score = max(0.0, ins["confidence_score"] - (penalty * 0.15))

        validated_insights.append(CompetitorInsight(
            competitor=comp,
            ci_dimension=ins["ci_dimension"],
            summary=ins["summary"],
            key_metrics=ins["key_metrics"],
            citations=verified_citations,
            confidence_score=round(adjusted_score, 2)
        ))

    return {
        "raw_insights": validated_insights,
        "validation_issues": issues,
        "current_agent": "validation_agent"
    }
```

---

### File 7: `backend/app/agents/orchestrator.py`
```python
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
        "iteration_count": state.get("iteration_count", 0) + 1
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
            "issues": issues
        }
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
            "rag_agent": "rag_agent"
        }
    )

    builder.add_edge("research_agent", "rag_agent")
    builder.add_edge("rag_agent", "analysis_agent")
    builder.add_edge("analysis_agent", "validation_agent")
    builder.add_edge("validation_agent", "report_assembler")
    builder.add_edge("report_assembler", END)

    return builder.compile()

ci_graph = build_ci_orchestrator()
```

---

## 5. Modifications to Existing Modules

### File: `backend/app/rag/pipeline.py`
Replace the execution logic in `compare_competitors` and `run_query` so they delegate to `ci_graph`:

```python
"""
app/rag/pipeline.py (LangGraph Delegation Wrapper)
"""
from typing import Dict, Any, Optional
from datetime import date
from app.agents.orchestrator import ci_graph
from app.agents.state import CIPipelineState
from app.core.config import settings
from app.core.cache import cache_get, cache_set

async def run_query(query: str, competitor: Optional[str] = None, ci_dimension: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
    cache_key_extra = f"{competitor or 'all'}::{ci_dimension or 'all'}"
    if use_cache:
        cached = await cache_get(query, cache_key_extra)
        if cached:
            return cached

    initial_state: CIPipelineState = {
        "query": query,
        "competitor": competitor,
        "ci_dimension": ci_dimension,
        "use_cache": use_cache,
        "needs_web_research": True,
        "current_agent": "init",
        "iteration_count": 0,
        "web_findings": [],
        "knowledge_base_chunks": [],
        "raw_insights": [],
        "validation_issues": [],
        "final_report": {},
        "errors": []
    }

    result = await ci_graph.ainvoke(initial_state)
    report = result.get("final_report", {})
    insights = list(report.get("competitors", {}).values())

    response = {
        "query": query,
        "summary": " ".join(i.get("summary", "") for i in insights[:3]),
        "key_metrics": [m for i in insights for m in i.get("key_metrics", [])][:20],
        "citations": [c for i in insights for c in i.get("citations", [])][:15],
        "confidence_score": report.get("overall_confidence", 0.0),
        "sub_query_count": len(insights)
    }

    if use_cache:
        await cache_set(query, response, cache_key_extra)
    return response

async def compare_competitors(ci_dimension: str, query: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
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
        "errors": []
    }

    result = await ci_graph.ainvoke(initial_state)
    report = result.get("final_report", {})

    output = {
        "ci_dimension": ci_dimension,
        "generated_at": date.today().isoformat(),
        "competitors": report.get("competitors", {}),
        "overall_confidence": report.get("overall_confidence", 0.0)
    }

    if use_cache:
        await cache_set(effective_query, output, cache_key)
    return output
```

---

## 6. Execution & Verification Steps

1. **Install new dependencies:**
   ```powershell
   cd D:\Data_Analytics_1\croma-ci-complete\croma-ci\backend
   venv\Scripts\pip install langgraph duckduckgo-search
   ```

2. **Verify services:**
   * PostgreSQL Docker container running on port `5435`.
   * Redis Docker container running on port `6379`.
   * Ollama running with `llama3.2` and `nomic-embed-text`.

3. **Start FastAPI Backend:**
   ```powershell
   backend\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Start Next.js Frontend:**
   ```powershell
   cd frontend
   npm run dev
   ```

5. **Test CI Matrix:**
   Open `http://localhost:3000` (or `http://localhost:3001`). The CI Matrix will now query through the 4-agent LangGraph workflow.

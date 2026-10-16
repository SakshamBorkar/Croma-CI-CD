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
    # User Input & Controls
    query: str
    competitor: Optional[str]
    ci_dimension: Optional[str]
    use_cache: bool
    user_id: Optional[str]

    # User-Controlled Agent Mode & Document Scope
    selected_mode: str  # "auto" | "research" | "rag" | "analysis" | "validation"
    source_scope: str   # "uploaded_only" | "croma_kb" | "uploaded_and_croma" | "all_sources"
    selected_document_ids: List[str]
    document_processing_status: Dict[str, Any]
    uploaded_document_references: List[Dict[str, Any]]

    # Orchestrator Dynamic Agent Selection
    needs_web_research: bool
    needs_rag_retrieval: bool
    selected_agents: List[str]
    plan_rationale: str
    current_agent: str
    iteration_count: int

    # Intermediate Agent Data
    web_findings: List[WebFinding]
    knowledge_base_chunks: List[RetrievedChunk]
    retrieved_document_chunks: List[RetrievedChunk]
    raw_insights: List[CompetitorInsight]
    nl_synthesis: Optional[str]
    validation_issues: List[ValidationIssue]
    missing_information: List[str]
    conflicts: List[Dict[str, Any]]

    # Final Result
    final_report: Dict[str, Any]
    errors: List[str]

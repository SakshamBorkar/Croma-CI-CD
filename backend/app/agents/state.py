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

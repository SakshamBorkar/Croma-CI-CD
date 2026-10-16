"""
app/api/routes/agentic.py
─────────────────────────
Dedicated Agentic Workflow endpoints:
  - POST /api/agentic/query            Execute user-controlled agent query
  - GET  /api/agentic/runs/{run_id}    Retrieve status and result of an execution run
"""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import UserContext, get_current_user
from app.rag.pipeline import run_query

agentic_router = APIRouter(prefix="/api/agentic", tags=["agentic"])

# In-memory run tracker for workflow runs
RUNS_STORE: Dict[str, Dict[str, Any]] = {}


class AgenticQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="Natural language query")
    selected_mode: str = Field(default="auto", description="Agent mode: auto | research | rag | analysis | validation")
    source_scope: str = Field(default="all_sources", description="Source scope: uploaded_only | croma_kb | uploaded_and_croma | all_sources")
    selected_document_ids: Optional[List[str]] = Field(default=[], description="List of specific uploaded document IDs to restrict to")
    competitor: Optional[str] = Field(default=None, description="Optional competitor slug filter")
    ci_dimension: Optional[str] = Field(default=None, description="Optional CI dimension filter")
    use_cache: bool = Field(default=True, description="Enable cache lookup")


class AgenticQueryResponse(BaseModel):
    run_id: str
    query: str
    selected_mode: str
    source_scope: str
    primary_agent: str
    summary: str
    key_metrics: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []
    confidence_score: float
    sub_query_count: int = 1
    competitors: Optional[Dict[str, Any]] = None
    validation_summary: Optional[Dict[str, Any]] = None
    missing_information: Optional[List[str]] = []
    conflicts: Optional[List[Dict[str, Any]]] = []
    agent_traces: Optional[Dict[str, Any]] = None


@agentic_router.post("/query", response_model=AgenticQueryResponse)
async def execute_agentic_query(
    body: AgenticQueryRequest,
    current_user: UserContext = Depends(get_current_user),
) -> AgenticQueryResponse:
    """
    Execute user-controlled agentic query with dynamic LangGraph routing
    and document scope filtering.
    """
    user_id = getattr(current_user, "email", None) or getattr(current_user, "username", "demo_user")
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    result = await run_query(
        query=body.query,
        competitor=body.competitor,
        ci_dimension=body.ci_dimension,
        use_cache=body.use_cache,
        selected_mode=body.selected_mode,
        source_scope=body.source_scope,
        selected_document_ids=body.selected_document_ids,
        user_id=user_id,
    )

    result_with_run = dict(result)
    result_with_run["run_id"] = run_id
    RUNS_STORE[run_id] = {
        "status": "completed",
        "result": result_with_run,
        "user_id": user_id,
    }

    return AgenticQueryResponse(**result_with_run)


@agentic_router.get("/runs/{run_id}", response_model=Dict[str, Any])
async def get_run_status(
    run_id: str,
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve run execution trace, status, and output."""
    user_id = getattr(current_user, "email", None) or getattr(current_user, "username", "demo_user")
    run = RUNS_STORE.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this run.")
    return run

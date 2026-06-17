"""
app/api/routes/query.py  — /api/query
app/api/routes/compare.py — /api/compare
app/api/routes/report.py  — /api/report/{competitor}  +  /api/report/export
app/api/routes/sources.py — /api/sources
app/api/routes/health.py  — /api/health
"""

# ─────────────────────────────────────────────────────────────────
# query.py
# ─────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from app.core.auth import UserContext, get_current_user
from app.core.config import settings
from app.rag.pipeline import run_query, compare_competitors, full_competitor_report

query_router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=500, description="Natural language query")
    competitor: Optional[str] = Field(None, description="Filter to a specific competitor slug")
    ci_dimension: Optional[str] = Field(None, description="Filter to a specific CI dimension")
    use_cache: bool = Field(True, description="Use Redis cache (set False to force fresh retrieval)")

    model_config = {"json_schema_extra": {
        "example": {
            "query": "How does Vijay Sales compare to Reliance Digital on store expansion?",
            "competitor": None,
            "ci_dimension": "geographical_presence",
        }
    }}


class QueryResponse(BaseModel):
    query: str
    summary: str
    key_metrics: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []
    confidence_score: float
    sub_query_count: int = 1


@query_router.post("/", response_model=QueryResponse)
async def free_form_query(
    body: QueryRequest,
    current_user: UserContext = Depends(get_current_user),
) -> QueryResponse:
    """Free-form NL query against the CI knowledge base."""
    if body.competitor and body.competitor not in settings.COMPETITORS:
        raise HTTPException(400, f"Unknown competitor. Valid: {settings.COMPETITORS}")
    if body.ci_dimension and body.ci_dimension not in settings.CI_DIMENSIONS:
        raise HTTPException(400, f"Unknown dimension. Valid: {settings.CI_DIMENSIONS}")

    result = await run_query(
        body.query,
        competitor=body.competitor,
        ci_dimension=body.ci_dimension,
        use_cache=body.use_cache,
    )
    return QueryResponse(**result)


# ─────────────────────────────────────────────────────────────────
# compare.py
# ─────────────────────────────────────────────────────────────────

compare_router = APIRouter(prefix="/api/compare", tags=["compare"])


class CompareRequest(BaseModel):
    ci_dimension: str = Field(..., description="CI dimension to compare across all competitors")
    query: Optional[str] = Field(None, description="Optional custom query (else auto-generated)")


@compare_router.post("/")
async def compare_all_competitors(
    body: CompareRequest,
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compare all 5 competitors on a single CI dimension."""
    if body.ci_dimension not in settings.CI_DIMENSIONS:
        raise HTTPException(400, f"Unknown dimension. Valid: {settings.CI_DIMENSIONS}")

    return await compare_competitors(body.ci_dimension, query=body.query)


# ─────────────────────────────────────────────────────────────────
# report.py
# ─────────────────────────────────────────────────────────────────

import io
from datetime import date

from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse

report_router = APIRouter(prefix="/api/report", tags=["report"])


@report_router.get("/{competitor}")
async def get_competitor_report(
    competitor: str,
    use_cache: bool = True,
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Full intelligence report for one competitor across all CI dimensions."""
    if competitor not in settings.COMPETITORS:
        raise HTTPException(400, f"Unknown competitor. Valid: {settings.COMPETITORS}")

    return await full_competitor_report(competitor, use_cache=use_cache)


@report_router.post("/export")
async def export_report(
    body: Dict[str, Any],
    current_user: UserContext = Depends(get_current_user),
) -> StreamingResponse:
    """
    Export CI report as PDF.
    Body: {"competitor": "vijay_sales", "format": "pdf"}
    """
    competitor = body.get("competitor")
    if not competitor or competitor not in settings.COMPETITORS:
        raise HTTPException(400, "Valid competitor required")

    report_data = await full_competitor_report(competitor)
    pdf_bytes = _generate_pdf(report_data)

    filename = f"croma_ci_{competitor}_{date.today()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


 


# ─────────────────────────────────────────────────────────────────
# sources.py
# ─────────────────────────────────────────────────────────────────

from fastapi import Query
from app.db.session import get_db
from app.db import crud
from sqlalchemy.ext.asyncio import AsyncSession

sources_router = APIRouter(prefix="/api/sources", tags=["sources"])


@sources_router.get("/")
async def list_ingested_sources(
    competitor: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all ingested documents with metadata (audit trail)."""
    sources = await crud.list_sources(db, competitor, source_type, limit, offset)
    return {
        "total": len(sources),
        "sources": [
            {
                "competitor": s.competitor,
                "source_type": s.source_type,
                "source_url": s.source_url,
                "publication_date": str(s.publication_date),
                "ingestion_date": str(s.ingestion_date),
                "chunk_count": s.chunk_count,
                "ci_dimensions": s.ci_dimensions,
                "status": s.status,
            }
            for s in sources
        ],
    }


# ─────────────────────────────────────────────────────────────────
# health.py
# ─────────────────────────────────────────────────────────────────

from datetime import datetime

health_router = APIRouter(prefix="/api/health", tags=["health"])


@health_router.get("/")
async def health_check() -> Dict[str, Any]:
    """Health check — returns service status and component availability."""
    import ollama as ol

    # Check Ollama
    try:
        models = ol.list()
        ollama_ok = True
        available_models = [m["name"] for m in models.get("models", [])]
    except Exception as e:
        ollama_ok = False
        available_models = []

    return {
        "status": "healthy" if ollama_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "ollama": {"ok": ollama_ok, "models": available_models},
            "api": {"ok": True},
        },
    }

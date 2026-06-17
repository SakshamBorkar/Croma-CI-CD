"""
app/main.py
────────────
FastAPI application factory.

Registers:
  - CORS middleware
  - Rate limiting (slowapi)
  - All API routers
  - Startup: DB init + Ollama model availability check
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import (
    compare_router,
    health_router,
    query_router,
    report_router,
    sources_router,
)
from app.core.auth import auth_router
from app.core.config import settings
from app.db.session import init_db

# ── Rate limiter ────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Croma CI Platform...")

    # Init database tables
    await init_db()
    logger.info("Database tables initialised")

    # Verify Ollama is reachable
    try:
        import ollama
        models_response = ollama.list()
        model_names = []
        if hasattr(models_response, 'models'):
            model_names = [m.model for m in models_response.models]
        elif isinstance(models_response, dict):
            model_names = [m.get("model", m.get("name", "")) for m in models_response.get("models", [])]
        logger.info(f"Ollama available. Models: {model_names}")

        if settings.OLLAMA_LLM_MODEL not in str(model_names):
            logger.warning(
                f"LLM model '{settings.OLLAMA_LLM_MODEL}' not found. "
                f"Run: ollama pull {settings.OLLAMA_LLM_MODEL}"
            )
        if settings.OLLAMA_EMBED_MODEL not in str(model_names):
            logger.warning(
                f"Embed model '{settings.OLLAMA_EMBED_MODEL}' not found. "
                f"Run: ollama pull {settings.OLLAMA_EMBED_MODEL}"
            )
    except Exception as e:
        logger.error(f"Ollama not reachable at {settings.OLLAMA_BASE_URL}: {e}")
        logger.warning("Starting in degraded mode — RAG queries will fail until Ollama is running.")

    yield  # ── App runs ───────────────────────────────────────────
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Gen AI Competitive Intelligence Platform for Croma",
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate limiting ───────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Routers ─────────────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(query_router)
    app.include_router(compare_router)
    app.include_router(report_router)
    app.include_router(sources_router)
    app.include_router(health_router)

    @app.get("/")
    async def root():
        return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

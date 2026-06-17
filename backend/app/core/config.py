"""
app/core/config.py
──────────────────
Central configuration via pydantic-settings.
All secrets come from environment variables / GCP Secret Manager (mounted as env vars).
Ollama replaces OpenAI / Cohere — models run 100% locally.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ─────────────────────────────────────────────────────
    APP_NAME: str = "Croma CI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://croma-ci.vercel.app"]

    # ── Ollama ──────────────────────────────────────────────────
    # Run `ollama pull mistral` or `ollama pull llama3` before starting
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama server URL")
    OLLAMA_LLM_MODEL: str = Field(default="mistral", description="Chat model: mistral | llama3 | llama3.1 | gemma2")
    OLLAMA_EMBED_MODEL: str = Field(default="nomic-embed-text", description="Embedding model; 768 dims")
    OLLAMA_EMBED_DIMS: int = 768          # nomic-embed-text output dims
    OLLAMA_TEMPERATURE: float = 0.1
    OLLAMA_MAX_TOKENS: int = 2000

    # ── ChromaDB (local vector store) ───────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_PREFIX: str = "croma_ci"

    # ── PostgreSQL ──────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://croma:croma@localhost:5432/croma_ci",
        description="Async SQLAlchemy URL",
    )
    DATABASE_ECHO: bool = False

    # ── Redis ───────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    RAG_CACHE_TTL_SECONDS: int = 86400    # 24 hours

    # ── Auth / JWT ──────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(default="CHANGE_ME_IN_PROD", description="HS256 secret key")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # ── RAG Pipeline ────────────────────────────────────────────
    CHUNK_SIZE: int = 500          # tokens
    CHUNK_OVERLAP: int = 50
    TOP_K_RETRIEVE: int = 20       # candidates from vector store
    TOP_K_RERANK: int = 5          # after BM25 re-ranking (no Cohere needed)
    BM25_WEIGHT: float = 0.4       # hybrid fusion: BM25 share
    DENSE_WEIGHT: float = 0.6      # hybrid fusion: embedding share

    # ── Scraping ────────────────────────────────────────────────
    SCRAPE_REQUEST_TIMEOUT: int = 30
    SCRAPE_CONCURRENCY: int = 5

    # ── Airflow / Slack Alerts ───────────────────────────────────
    SLACK_WEBHOOK_URL: str = Field(default="", description="Slack webhook for CI alerts")
    CHANGE_DETECTION_THRESHOLD: float = 0.05   # 5% delta triggers alert

    # ── Competitors ─────────────────────────────────────────────
    COMPETITORS: List[str] = [
        "reliance_digital",
        "vijay_sales",
        "aditya_vision",
        "poojara",
        "bajaj_electronics",
    ]

    CI_DIMENSIONS: List[str] = [
        "business_model",
        "geographical_presence",
        "financial_performance",
        "customer_feedback",
        "strategic_initiatives",
        "future_outlook",
    ]

    @model_validator(mode="after")
    def resolve_chroma_path(self) -> "Settings":
        from pathlib import Path
        if self.CHROMA_PERSIST_DIR.startswith("./"):
            # Resolve relative to the backend root directory (which is two levels up from this file)
            backend_root = Path(__file__).resolve().parents[2]
            self.CHROMA_PERSIST_DIR = str((backend_root / self.CHROMA_PERSIST_DIR[2:]).resolve())
        return self


settings = Settings()


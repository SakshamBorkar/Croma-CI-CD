# Croma CI Platform — Complete Setup Guide

> **Gen AI Competitive Intelligence for Indian Electronics Retail**  
> Stack: FastAPI · Ollama (local LLM) · ChromaDB · PostgreSQL · Redis · Airflow · Next.js 14

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                        │
│  CI Matrix │ NL Search │ Competitor Reports │ Sources │ Health       │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ REST + JWT
┌─────────────────────────▼───────────────────────────────────────────┐
│                       BACKEND (FastAPI)                              │
│  /api/query  /api/compare  /api/report  /api/sources  /api/health   │
│                                                                      │
│  RAG Pipeline:                                                       │
│  Query → Decompose → [Embed → ChromaDB Dense] + [BM25 Sparse]       │
│       → RRF Fusion → Ollama LLM → Structured JSON answer            │
└──────┬──────────────────┬──────────────────────┬───────────────────┘
       │                  │                       │
┌──────▼──────┐  ┌────────▼────────┐  ┌──────────▼──────────┐
│  Ollama     │  │   ChromaDB      │  │  PostgreSQL + Redis  │
│  mistral    │  │  (local vector  │  │  metadata · cache    │
│  nomic-     │  │   store, 5      │  │  snapshots · reports │
│  embed-text │  │   collections)  │  │                      │
└─────────────┘  └─────────────────┘  └──────────────────────┘
       ▲
┌──────┴────────────────────────────────────────────────────────────┐
│                    AIRFLOW DAGs                                    │
│  ci_ingestion_weekly  (Sun 02:00 IST) — full scrape + embed      │
│  ci_news_daily        (Daily 06:00 IST) — RSS news               │
│  ci_report_generate   (Mon 07:00 IST) — generate + store reports │
└───────────────────────────────────────────────────────────────────┘
```

---

## 1. Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend |
| Node.js | 20+ | Frontend |
| Docker + Compose | Latest | Local stack |
| Ollama | Latest | Local LLM |
| PostgreSQL | 16 | Metadata store |
| Redis | 7 | Query cache |

---

## 2. Ollama Setup (Do This First)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull mistral              # Chat/generation model (~4GB)
ollama pull nomic-embed-text     # Embedding model (~274MB, 768-dim)

# Verify
ollama list
ollama serve                     # Starts on http://localhost:11434
```

**Alternative models** (set in `.env`):
| Model | Size | Notes |
|-------|------|-------|
| `llama3` | 4.7GB | Better reasoning |
| `llama3.1` | 4.7GB | Latest Meta |
| `gemma2` | 5.4GB | Google, good summaries |
| `phi3` | 2.3GB | Lightweight |
| `mxbai-embed-large` | 670MB | 1024-dim embeds |

---

## 3. Option A — Docker Compose (Recommended)

```bash
git clone <repo>
cd croma-ci

# Configure environment
cp .env.example .env
# Edit .env — set SLACK_WEBHOOK_URL if you want alerts

# Start full stack
docker-compose up -d

# Pull Ollama models inside container
docker exec croma-ollama ollama pull mistral
docker exec croma-ollama ollama pull nomic-embed-text

# Verify all services
docker-compose ps
```

**Service URLs:**
- Frontend: http://localhost:3000 *(deploy separately with npm run dev)*
- Backend API: http://localhost:8000/docs
- Airflow: http://localhost:8080 (admin/admin)
- Ollama: http://localhost:11434

---

## 4. Option B — Manual Setup

### 4.1 Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Install Playwright browsers (for dynamic page scraping)
playwright install chromium

# Configure
cp ../.env.example .env
# Edit .env — verify OLLAMA_BASE_URL, DATABASE_URL, REDIS_URL

# Run migrations (first time)
python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.2 Frontend

```bash
cd frontend
npm install
cp ../.env.example .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> .env.local
npm run dev
```

### 4.3 Airflow

```bash
pip install apache-airflow==2.9.1
export AIRFLOW_HOME=./airflow_home
airflow db migrate
airflow users create --username admin --password admin \
  --firstname Admin --lastname User --role Admin --email admin@croma.com

# Copy DAGs
cp dags/*.py $AIRFLOW_HOME/dags/

airflow webserver --port 8080 &
airflow scheduler &
```

---

## 5. Running the Ingestion Pipeline

### Trigger manually (first run):
```bash
# Via Airflow UI → DAGs → ci_ingestion_weekly → Trigger
# Or CLI:
airflow dags trigger ci_ingestion_weekly
```

### Or run the ingestion script directly:
```bash
cd backend
python -m app.ingestion.run_once  # (one-shot ingestion script)
```

---

## 6. Project Structure

```
croma-ci/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # All settings (Ollama URLs, model names)
│   │   │   ├── auth.py            # JWT auth + demo login
│   │   │   └── cache.py           # Redis cache helpers
│   │   ├── db/
│   │   │   ├── models.py          # SQLAlchemy ORM models
│   │   │   ├── session.py         # Async DB session factory
│   │   │   └── crud.py            # CRUD operations
│   │   ├── ingestion/
│   │   │   ├── scraper.py         # Static (httpx) + Dynamic (Playwright) scraper
│   │   │   ├── pdf_extractor.py   # PyMuPDF + pdfplumber
│   │   │   ├── chunker.py         # LangChain chunker + metadata schema
│   │   │   ├── embedder.py        # Ollama nomic-embed-text
│   │   │   └── upserter.py        # ChromaDB upsert + query
│   │   ├── rag/
│   │   │   ├── retriever.py       # Hybrid BM25 + Dense + RRF fusion
│   │   │   ├── decomposer.py      # Query decomposition via Ollama
│   │   │   ├── generator.py       # Ollama LLM + hallucination guard
│   │   │   └── pipeline.py        # Full orchestrator
│   │   ├── api/routes/
│   │   │   └── __init__.py        # All FastAPI routes
│   │   └── main.py                # App factory + lifespan
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx           # Root dashboard (auth gate + tabs)
│       │   └── globals.css
│       ├── components/
│       │   ├── CompetitorMatrix.tsx   # 6×5 CI matrix grid
│       │   ├── DrillDown.tsx          # Slide-over detail panel
│       │   ├── SearchBar.tsx          # NL search + results
│       │   ├── ReportView.tsx         # Full report per competitor
│       │   ├── SourcesTable.tsx       # Ingested sources audit
│       │   ├── CitationBadge.tsx      # Source citation card
│       │   └── LoginPage.tsx          # JWT login form
│       └── lib/
│           └── api.ts                 # Type-safe API client
├── dags/
│   ├── ci_ingestion_weekly.py     # Sunday full scrape
│   └── ci_news_daily.py           # Daily news + Monday reports
├── tests/
│   └── test_rag_pipeline.py       # pytest full coverage
├── .github/workflows/ci.yml       # GitHub Actions CI/CD
├── docker-compose.yml
└── .env.example
```

---

## 7. Key Design Decisions (Ollama vs OpenAI)

| Component | OpenAI/Cohere (original) | Ollama (this build) |
|-----------|--------------------------|---------------------|
| LLM       | gpt-4-turbo              | mistral / llama3    |
| Embeddings | text-embedding-3-small  | nomic-embed-text    |
| Re-ranking | Cohere Rerank           | BM25 + RRF fusion   |
| Vector DB  | Pinecone                | ChromaDB (local)    |
| Cost       | ~$50–200/month           | **$0 (local)**      |
| Privacy    | Data leaves premises     | **100% local**      |

---

## 8. Running Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v --tb=short

# With coverage
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

---

## 9. Switching Ollama Models

Edit `.env`:
```bash
OLLAMA_LLM_MODEL=llama3           # better reasoning, larger context
OLLAMA_EMBED_MODEL=mxbai-embed-large  # 1024-dim, better quality
```

Then `ollama pull llama3 && ollama pull mxbai-embed-large` and restart backend.

> **Note:** If you change embedding models, you must re-embed all chunks.  
> Delete `./chroma_db/` and re-run the ingestion DAG.

---

## 10. Production Deployment Checklist

- [ ] Set `JWT_SECRET_KEY` to a 32+ char random string
- [ ] Replace demo login with Azure AD OIDC (see `auth.py` comments)
- [ ] Deploy Ollama on a GPU VM (GCP `n1-standard-4` + T4 GPU recommended)
- [ ] Set `OLLAMA_BASE_URL` to the GPU VM's internal IP
- [ ] Run ChromaDB as a server (`chroma run --host 0.0.0.0`) or switch to Pinecone
- [ ] Set `SLACK_WEBHOOK_URL` for change detection alerts
- [ ] Enable Airflow `celery` executor for production scale
- [ ] Configure GCP Cloud Run auto-scaling (see `.github/workflows/ci.yml`)

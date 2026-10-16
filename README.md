# Croma CI Platform — Multi-Agent Architecture

> **Gen AI Competitive Intelligence for Indian Electronics Retail**  
> **Stack:** FastAPI · LangGraph Orchestrator · Groq Cloud LLM (120B) · Local ONNX Embeddings · ChromaDB · PostgreSQL · Redis · Next.js 14 · Docker Compose · GitHub Actions CI/CD

---

## 1. System Architecture & Workflow

The platform leverages a **LangGraph state machine** to dynamically orchestrate specialized AI agents across real-time web research, vector search, financial analysis, and citation validation.

```
                                ┌────────────────┐
                                │   User Query   │
                                └───────┬────────┘
                                        │
                                        ▼
                        ┌────────────────────────────────┐
                        │    Orchestrator — LangGraph    │
                        │ Dynamic Planning & Mode Router │
                        └───────┬───────────────┬────────┘
                                │               │
             ┌──────────────────┴──┐         ┌──┴──────────────────┐
             ▼                     ▼         ▼                     ▼
   ┌──────────────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐
   │  Research Agent  │  │ RAG Agent │  │ Analysis  │  │ Validation Agent │
   │ Live Web Scrape  │  │ ChromaDB  │  │   Agent   │  │ Citation Audit & │
   │  & Playwright    │  │  + BM25   │  │ Groq 120B │  │ Fact Consistency │
   └──────────────────┘  └───────────┘  └───────────┘  └──────────────────┘
             │                 │               │                 │
             └─────────────────┴───────┬───────┴─────────────────┘
                                       │
                                       ▼
                             ┌───────────────────┐
                             │   Final Report    │
                             │ Evidence Synthesis│
                             │  & Metrics Table  │
                             └───────────────────┘
```

---

## 2. Multi-Agent Workflow Modes

The orchestrator operates in **5 configurable execution modes**:

| Mode | Primary Agent | Workflow Description |
| :--- | :--- | :--- |
| **Auto (Default)** | **Orchestrator** | Dynamically analyzes user query intent. Triggers live web search for recent pricing/promotions and RAG retrieval across corporate filings, then synthesizes with Groq 120B and validates facts. |
| **Research Mode** | **Research Agent** | Focuses on live web intelligence, search engine discovery (DuckDuckGo), and dynamic webpage crawling via Playwright/HTTPX. |
| **RAG Mode** | **RAG Agent** | Performs hybrid retrieval (dense ChromaDB embeddings + sparse BM25 keyword matching fused via Reciprocal Rank Fusion) across user documents and knowledge bases. |
| **Analysis Mode** | **Analysis Agent** | Performs deep cross-competitor comparative analysis, KPI extraction, and structured tabular trend breakdowns. |
| **Validation Mode** | **Validation Agent** | Cross-references extracted facts against source documents, audits citation integrity, and calculates calibrated confidence scores. |

### Document Vault & Knowledge Scopes
Users can upload custom documents (PDF, Word, Excel, CSV, Text) into an in-memory & vector vault with flexible querying scopes:
- `all_sources`: Blends curated corporate filings, uploaded documents, and live web hits.
- `uploaded_only`: Strict retrieval bounded exclusively to user-uploaded files.
- `croma_kb`: Internal Croma intelligence filings only.
- `uploaded_and_croma`: Combines uploaded documents with internal intelligence.

---

## 3. Technology Stack

- **Backend**: Python 3.11+ · FastAPI · LangGraph · LangChain · SQLAlchemy (Async) · Pydantic v2
- **LLM & Embeddings**: Groq Cloud (`openai/gpt-oss-120b`) · Local ONNX (`all-MiniLM-L6-v2`, 384 dims) · Ollama fallback (`mistral` / `nomic-embed-text`)
- **Data Stores**: ChromaDB (Vector store) · PostgreSQL 16 (Metadata & Documents) · Redis 7 (Query & RAG cache)
- **Frontend**: Next.js 14 (App Router, Standalone build) · React 18 · Tailwind CSS · TypeScript
- **DevOps & CI/CD**: Docker & Docker Compose · GitHub Actions (multi-stage pipeline with Postgres & Redis service containers)

---

## 4. Quick Start Guide

### Prerequisites
- **Docker & Docker Compose** (Latest)
- **Python 3.11+** (for manual backend run)
- **Node.js 20+** (for manual frontend run)

---

### Option A: Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SakshamBorkar/Croma-CI-CD.git
   cd Croma-CI-CD
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   *(Ensure `GROQ_API_KEY` is set in `.env` for high-speed cloud inference, or use local Ollama)*

3. **Build and start the core stack:**
   ```bash
   # Build images
   docker compose build backend frontend

   # Start containers in background
   docker compose up -d backend frontend
   ```

4. **Verify container status:**
   ```bash
   docker compose ps
   ```

   **Service Access Points:**
   - **Frontend UI:** [http://localhost:3000](http://localhost:3000)
   - **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Backend Health Check:** [http://localhost:8000/api/health/](http://localhost:8000/api/health/)
   - **PostgreSQL Database:** `localhost:5435` *(mapped to container port 5432)*
   - **Redis Cache:** `localhost:6379`
   - **Ollama (Optional):** `localhost:11434`

---

### Option B: Local Manual Setup

#### 1. Start Supporting Services (Postgres & Redis)
```bash
docker compose up -d postgres redis ollama
```
*(PostgreSQL runs on port `5435` to avoid conflicts with existing local Postgres instances).*

#### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser dependencies (for web scraper)
playwright install chromium

# Initialize PostgreSQL database tables
python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"

# Start the FastAPI server with live reload
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 3. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.  
*(In local dev mode, any username and password can be entered to log in, e.g. `admin` / `admin`)*.

---

## 5. Automated CI/CD Pipeline (GitHub Actions)

Every pull request and push to `main` triggers a complete 3-stage GitHub Actions pipeline (`.github/workflows/ci.yml`):

```
┌─────────────────────────────────┐
│ Stage 1: Backend Tests & Lint   │
│ - Spins up Postgres & Redis     │
│ - Sets up Python 3.11 with pip  │
│ - Runs all 35 pytest unit tests │
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│ Stage 2: Frontend Check & Build │
│ - TypeScript type checking      │
│ - ESLint validation             │
│ - Next.js Standalone build      │
└───────────────┬─────────────────┘
                │
┌───────────────▼─────────────────┐
│ Stage 3: Docker Build Check     │
│ - Validates docker-compose.yml  │
│ - Builds Backend Docker image   │
│ - Builds Frontend Docker image  │
└─────────────────────────────────┘
```

### Running Tests Locally

```powershell
# Run backend pytest suite (all 35 tests)
pytest tests/ -v

# Run frontend type and lint checks
cd frontend
npm run type-check
npm run lint
npm run build
```

### Testing Inside Docker Container

```powershell
# Run the test suite inside an isolated Docker container
docker run --rm -v ${PWD}/tests:/app/tests croma-ci-backend:latest pytest tests/ -v
```

---

## 6. Project Structure

```
croma-ci/
├── .github/
│   └── workflows/
│       └── ci.yml               # Complete GitHub Actions CI/CD pipeline
├── backend/
│   ├── app/
│   │   ├── agents/              # LangGraph Multi-Agent System
│   │   │   ├── orchestrator.py  # Graph definition & dynamic mode router
│   │   │   ├── research_agent.py# Web search & Playwright scraper
│   │   │   ├── rag_agent.py     # Hybrid dense ChromaDB + BM25 search
│   │   │   ├── analysis_agent.py# Groq 120B comparison & synthesis
│   │   │   ├── validation_agent.py # Fact consistency & citations
│   │   │   └── state.py         # Shared pipeline TypedDict state
│   │   ├── api/routes/          # FastAPI routers (query, compare, docs, etc.)
│   │   ├── core/                # Config, JWT auth, CORS middleware, Redis
│   │   ├── db/                  # SQLAlchemy models & async session
│   │   ├── ingestion/           # Scrapers, PDF extractors, chunkers
│   │   ├── rag/                 # Fusion retriever & generator
│   │   └── main.py              # FastAPI app factory
│   ├── requirements.txt         # Backend Python dependencies
│   └── Dockerfile               # Multi-stage production container
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router & main dashboard
│   │   ├── components/          # Agent workflow, document vault, matrix
│   │   └── lib/api.ts           # Type-safe API client
│   ├── package.json
│   ├── next.config.mjs          # Standalone output configuration
│   ├── .eslintrc.json           # ESLint configuration
│   └── Dockerfile               # Multi-stage Next.js production container
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_agents.py           # Unit tests for multi-agent execution
│   ├── test_document_and_modes.py# Mode routing & document vault tests
│   └── test_rag_pipeline.py     # Hybrid RAG & API endpoint tests
├── docker-compose.yml           # Multi-service stack (Frontend, Backend, DB, Redis)
└── README.md
```

---

## 7. Configuration Reference (`.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | *(Required for cloud LLM)* | Groq API key for fast 120B parameter model inference |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Model used for natural language analysis and synthesis |
| `EMBEDDING_PROVIDER` | `local` | `local` (ONNX fast embeddings) or `ollama` |
| `LOCAL_EMBED_MODEL` | `all-MiniLM-L6-v2` | Fast 384-dim ONNX local embedding model |
| `DATABASE_URL` | `postgresql+asyncpg://...:5435/croma_ci` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis caching connection string |
| `ALLOWED_ORIGINS` | `["http://localhost:3000", ...]` | CORS allowed origins list |
| `JWT_SECRET_KEY` | *(Change in production)* | JWT signing secret |

---

## 8. License & Attribution

Built for the **Croma Competitive Intelligence Platform** — Tata Electronics Retail Analytics.  
Open-source under the Apache 2.0 License.

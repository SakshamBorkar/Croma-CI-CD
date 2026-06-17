"""
tests/test_rag_pipeline.py
───────────────────────────
pytest tests for:
  - Chunker
  - Embedder (mock Ollama)
  - Retriever (mock ChromaDB)
  - Generator (mock Ollama)
  - Pipeline
  - API endpoints
"""

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any


# ─── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def sample_content_blocks():
    return [
        {"type": "text", "content": "Vijay Sales operates 100 stores across Maharashtra and Delhi NCR as of 2024.", "page": 1},
        {"type": "table", "content": "| State | Stores |\n|-------|--------|\n| Maharashtra | 60 |\n| Delhi | 40 |", "page": 2},
        {"type": "text", "content": "The company reported revenue of Rs 2,500 crore in FY2024 with 15% YoY growth.", "page": 3},
    ]


@pytest.fixture
def sample_chunks(sample_content_blocks):
    from app.ingestion.chunker import chunk_document
    return chunk_document(
        sample_content_blocks,
        competitor="vijay_sales",
        source_type="annual_report",
        source_url="https://vijaysales.com/annual-report-2024.pdf",
        publication_date="2024-06-01",
    )


@pytest.fixture
def mock_embedding():
    return [0.1] * 768  # nomic-embed-text produces 768-dim vectors


# ─── Chunker tests ────────────────────────────────────────────────

class TestChunker:
    def test_produces_chunks(self, sample_content_blocks):
        from app.ingestion.chunker import chunk_document
        chunks = chunk_document(
            sample_content_blocks, "vijay_sales", "annual_report",
            "https://example.com/ar.pdf", "2024-01-01"
        )
        assert len(chunks) > 0

    def test_metadata_schema_complete(self, sample_chunks):
        """Every chunk must carry all required metadata fields."""
        required_fields = [
            "text", "competitor", "source_type", "source_url",
            "publication_date", "ingestion_date", "ci_dimensions",
            "chunk_index", "content_hash",
        ]
        for chunk in sample_chunks:
            for field in required_fields:
                assert field in chunk, f"Missing field: {field}"

    def test_table_not_split(self, sample_content_blocks):
        """Tables must remain as single chunks."""
        from app.ingestion.chunker import chunk_document
        table_block = [{"type": "table", "content": "| A | B |\n|---|---|\n" + "| row | data |\n" * 50, "page": 1}]
        chunks = chunk_document(table_block, "vijay_sales", "website", "http://x.com")
        table_chunks = [c for c in chunks if c.get("block_type") == "table"]
        # Table should produce exactly one chunk regardless of size
        assert len(table_chunks) == 1

    def test_content_hash_unique(self, sample_chunks):
        """Content hashes must be unique."""
        hashes = [c["content_hash"] for c in sample_chunks]
        assert len(hashes) == len(set(hashes))

    def test_competitor_set_correctly(self, sample_chunks):
        for chunk in sample_chunks:
            assert chunk["competitor"] == "vijay_sales"

    def test_ci_dimensions_auto_classified(self, sample_chunks):
        """At least some chunks should have auto-classified dimensions."""
        all_dims = [d for c in sample_chunks for d in c.get("ci_dimensions", [])]
        assert len(all_dims) > 0


# ─── Embedder tests ───────────────────────────────────────────────

class TestEmbedder:
    @patch("app.ingestion.embedder.ollama")
    def test_embed_single(self, mock_ollama):
        mock_ollama.embeddings.return_value = {"embedding": [0.1] * 768}
        from app.ingestion.embedder import embed_single
        result = embed_single("test text")
        assert len(result) == 768
        mock_ollama.embeddings.assert_called_once()

    @patch("app.ingestion.embedder.ollama")
    @pytest.mark.asyncio
    async def test_embed_chunks_batch(self, mock_ollama, sample_chunks):
        mock_ollama.embeddings.return_value = {"embedding": [0.1] * 768}
        from app.ingestion.embedder import embed_chunks_batch

        result = await embed_chunks_batch(sample_chunks[:3])
        for chunk in result:
            assert "embedding" in chunk
            assert len(chunk["embedding"]) == 768


# ─── Retriever tests ──────────────────────────────────────────────

class TestRetriever:
    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_single_async")
    @patch("app.rag.retriever.query_collection")
    async def test_retrieve_returns_chunks(self, mock_query, mock_embed, mock_embedding):
        mock_embed.return_value = mock_embedding
        mock_query.return_value = [
            {
                "id": "abc123",
                "text": "Vijay Sales has 100 stores in Maharashtra.",
                "metadata": {"source_url": "https://vijaysales.com", "publication_date": "2024-01-01"},
                "distance": 0.1,
                "score": 0.9,
            }
        ]

        from app.rag.retriever import retrieve
        results = await retrieve("Vijay Sales store count", competitor="vijay_sales", top_k_final=5)

        assert len(results) > 0
        assert "text" in results[0]
        assert "score" in results[0] or "rrf_score" in results[0]

    @pytest.mark.asyncio
    @patch("app.rag.retriever.embed_single_async")
    @patch("app.rag.retriever.query_collection")
    async def test_retrieve_empty_returns_empty(self, mock_query, mock_embed, mock_embedding):
        mock_embed.return_value = mock_embedding
        mock_query.return_value = []

        from app.rag.retriever import retrieve
        results = await retrieve("unknown query", competitor="poojara")
        assert results == []


# ─── Generator tests ──────────────────────────────────────────────

class TestGenerator:
    MOCK_RESPONSE = {
        "summary": "Vijay Sales operates 100 stores with strong Maharashtra presence.",
        "key_metrics": [{"metric": "Store count", "value": "100", "period": "2024"}],
        "citations": [{"source": "https://vijaysales.com/ar.pdf", "date": "2024-06-01", "excerpt": "100 stores across Maharashtra"}],
        "confidence_score": 0.85,
    }

    @patch("app.rag.generator.ollama")
    def test_generate_returns_structured_json(self, mock_ollama):
        mock_ollama.chat.return_value = {
            "message": {"content": json.dumps(self.MOCK_RESPONSE)}
        }

        from app.rag.generator import generate_answer
        context_chunks = [
            {
                "text": "Vijay Sales operates 100 stores in Maharashtra.",
                "metadata": {"source_url": "https://vijaysales.com/ar.pdf", "publication_date": "2024-06-01"},
            }
        ]
        result = generate_answer("store count", context_chunks, "vijay_sales", "geographical_presence")

        assert "summary" in result
        assert "key_metrics" in result
        assert "citations" in result
        assert "confidence_score" in result
        assert isinstance(result["confidence_score"], float)

    @patch("app.rag.generator.ollama")
    def test_hallucination_guard_removes_invalid_citation(self, mock_ollama):
        """Citation from unknown source should be removed."""
        response_with_bad_citation = dict(self.MOCK_RESPONSE)
        response_with_bad_citation["citations"] = [
            {"source": "https://totally-fake-domain.xyz/made-up.pdf", "date": "2024-01-01", "excerpt": "invented fact"}
        ]
        mock_ollama.chat.return_value = {
            "message": {"content": json.dumps(response_with_bad_citation)}
        }

        from app.rag.generator import generate_answer
        context_chunks = [
            {"text": "Real content.", "metadata": {"source_url": "https://vijaysales.com", "publication_date": "2024"}}
        ]
        result = generate_answer("test", context_chunks, "vijay_sales")
        # The bad citation should be filtered
        for cit in result.get("citations", []):
            assert "totally-fake-domain" not in cit.get("source", "")


# ─── Decomposer tests ─────────────────────────────────────────────

class TestDecomposer:
    @patch("app.rag.decomposer.ollama")
    def test_decompose_returns_list(self, mock_ollama):
        mock_ollama.chat.return_value = {
            "message": {"content": '["Vijay Sales store count 2024", "Vijay Sales expansion plans"]'}
        }
        from app.rag.decomposer import decompose_query
        result = decompose_query("How many stores does Vijay Sales have?")
        assert isinstance(result, list)
        assert len(result) >= 1

    @patch("app.rag.decomposer.ollama")
    def test_decompose_falls_back_on_error(self, mock_ollama):
        mock_ollama.chat.side_effect = Exception("Ollama down")
        from app.rag.decomposer import decompose_query
        result = decompose_query("Some query")
        # Should return original query as fallback
        assert result == ["Some query"]


# ─── API endpoint tests ───────────────────────────────────────────

from fastapi.testclient import TestClient

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Get a valid JWT token for testing."""
    from app.core.auth import create_access_token
    token = create_access_token({"sub": "test_user", "roles": ["analyst"]})
    return {"Authorization": f"Bearer {token}"}


class TestAPIEndpoints:
    def test_health_check(self, client):
        response = client.get("/api/health/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_query_requires_auth(self, client):
        response = client.post("/api/query/", json={"query": "test query"})
        assert response.status_code == 401

    @patch("app.api.routes.run_query")
    def test_query_returns_answer(self, mock_run, client, auth_headers):
        mock_run.return_value = {
            "query": "test",
            "summary": "Test summary",
            "key_metrics": [],
            "citations": [],
            "confidence_score": 0.7,
            "sub_query_count": 2,
        }
        response = client.post(
            "/api/query/",
            json={"query": "How many stores does Vijay Sales have?"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "confidence_score" in data

    def test_query_invalid_competitor_returns_400(self, client, auth_headers):
        response = client.post(
            "/api/query/",
            json={"query": "test query", "competitor": "unknown_brand"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    @patch("app.api.routes.compare_competitors")
    def test_compare_endpoint(self, mock_compare, client, auth_headers):
        mock_compare.return_value = {
            "ci_dimension": "financial_performance",
            "generated_at": "2024-01-01",
            "competitors": {},
        }
        response = client.post(
            "/api/compare/",
            json={"ci_dimension": "financial_performance"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_sources_endpoint_requires_auth(self, client):
        response = client.get("/api/sources/")
        assert response.status_code == 401

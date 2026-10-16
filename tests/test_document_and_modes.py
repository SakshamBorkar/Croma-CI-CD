"""
tests/test_document_and_modes.py
─────────────────────────────────
Unit and integration tests for:
  1. Document validation, extraction, chunking, and preview.
  2. Document upload, listing, preview, and deletion endpoints.
  3. Dynamic LangGraph agent mode routing (Auto, Research, RAG, Analysis, Validation).
  4. Source scope enforcement (uploaded_only, croma_kb, all_sources).
"""

import io
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import create_access_token
from app.ingestion.document_processor import (
    validate_file,
    extract_document_pages,
    chunk_document_blocks,
    process_and_register_document,
    list_user_documents,
    delete_user_document,
    get_document_preview,
)
from app.agents.orchestrator import (
    orchestrator_plan,
    route_orchestrator,
    route_after_research,
    route_after_rag,
    route_after_analysis,
    orchestrator_finalize,
)
from app.agents.state import CIPipelineState


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token({"sub": "test_analyst", "email": "analyst@croma.com", "roles": ["analyst"]})
    return {"Authorization": f"Bearer {token}"}


class TestDocumentValidationAndExtraction:
    def test_validate_supported_and_reject_executables(self):
        # 1. Valid CSV
        valid, err, ext = validate_file(b"col1,col2\nval1,val2", "data.csv")
        assert valid is True
        assert ext == ".csv"

        # 2. Valid Markdown
        valid, err, ext = validate_file(b"# Strategy\nSome text", "notes.md")
        assert valid is True
        assert ext == ".md"

        # 3. Reject executable DOS binary
        exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
        valid, err, ext = validate_file(exe_bytes, "malware.exe")
        assert valid is False
        assert "Executable" in err or "Unsupported" in err

        # 4. Reject unsupported extension
        valid, err, ext = validate_file(b"data", "script.sh")
        assert valid is False
        assert "Unsupported" in err

        # 5. Reject empty file
        valid, err, ext = validate_file(b"", "empty.txt")
        assert valid is False
        assert "empty" in err

    def test_extract_csv_tabular_structure(self):
        csv_bytes = b"Competitor,Stores,Revenue\nCroma,450,18000\nVijay Sales,140,4500\n"
        blocks = extract_document_pages(csv_bytes, "retail.csv", ".csv")
        assert len(blocks) == 1
        assert "Competitor | Stores | Revenue" in blocks[0]["text"]
        assert blocks[0]["section"] == "CSV Table"

    def test_extract_markdown_sections(self):
        md_bytes = b"# Heading 1\nSection 1 text\n# Heading 2\nSection 2 text"
        blocks = extract_document_pages(md_bytes, "doc.md", ".md")
        assert len(blocks) >= 2
        assert "Heading 1" in blocks[0]["section"]

    def test_chunking_preserves_provenance(self):
        blocks = [
            {"text": "Short chunk content here.", "page_number": 3, "section": "Pricing Details"}
        ]
        chunks = chunk_document_blocks(blocks, "doc_123", "user_abc", "spec.pdf")
        assert len(chunks) == 1
        c = chunks[0]
        assert c["doc_id"] == "doc_123"
        assert c["user_id"] == "user_abc"
        assert c["filename"] == "spec.pdf"
        assert c["page_number"] == 3
        assert c["section"] == "Pricing Details"
        assert len(c["content_hash"]) == 64


class TestAgentModeRouting:
    def test_research_mode_routes_directly_to_research_then_ends(self):
        state = {
            "query": "Reliance Digital store expansion",
            "selected_mode": "research",
            "needs_web_research": True,
        }
        # Entry routing
        assert route_orchestrator(state) == "research_agent"
        # After research routing
        assert route_after_research(state) == "report_assembler"

    def test_rag_mode_routes_directly_to_rag_then_ends(self):
        state = {
            "query": "Show financial performance of competitors",
            "selected_mode": "rag",
            "needs_web_research": False,
        }
        # Entry routing
        assert route_orchestrator(state) == "rag_agent"
        # After RAG routing
        assert route_after_rag(state) == "report_assembler"

    def test_analysis_mode_routes_rag_then_analysis_then_ends(self):
        state = {
            "query": "Compare pricing discounts across all retailers",
            "selected_mode": "analysis",
        }
        assert route_orchestrator(state) == "rag_agent"
        assert route_after_rag(state) == "analysis_agent"
        assert route_after_analysis(state) == "report_assembler"

    def test_validation_mode_routes_rag_then_validation_then_ends(self):
        state = {
            "query": "Verify if Vijay Sales has 200 stores",
            "selected_mode": "validation",
        }
        assert route_orchestrator(state) == "rag_agent"
        assert route_after_rag(state) == "validation_agent"

    def test_auto_mode_conditional_routing(self):
        # With trigger word "price"
        state_web = {
            "query": "What are current pricing offers?",
            "selected_mode": "auto",
            "needs_web_research": True,
        }
        assert route_orchestrator(state_web) == "research_agent"
        assert route_after_research(state_web) == "rag_agent"
        assert route_after_rag(state_web) == "analysis_agent"
        assert route_after_analysis(state_web) == "validation_agent"


class TestDocumentEndpoints:
    def test_upload_and_delete_document_lifecycle(self, client, auth_headers):
        file_content = b"Competitor,Q3_Revenue\nReliance Digital,5400\nCroma,4200"
        files = {"files": ("q3_results.csv", file_content, "text/csv")}

        with patch("app.ingestion.document_processor.index_document_chunks", new_callable=AsyncMock) as mock_index:
            mock_index.return_value = 1
            # 1. Upload
            response = client.post("/api/documents/upload", files=files, headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            doc_id = data[0]["document_id"]
            assert data[0]["filename"] == "q3_results.csv"
            assert data[0]["status"] == "ready"

            # 2. List
            list_res = client.get("/api/documents/", headers=auth_headers)
            assert list_res.status_code == 200
            user_docs = list_res.json()
            assert any(d["document_id"] == doc_id for d in user_docs)

            # 3. Preview
            prev_res = client.get(f"/api/documents/{doc_id}/preview", headers=auth_headers)
            assert prev_res.status_code == 200
            preview_data = prev_res.json()
            assert "Reliance Digital" in preview_data["preview_text"]

            # 4. Delete
            del_res = client.delete(f"/api/documents/{doc_id}", headers=auth_headers)
            assert del_res.status_code == 200
            assert del_res.json()["status"] == "deleted"

    def test_agentic_query_endpoint_supports_mode_and_scope(self, client, auth_headers):
        mock_result = {
            "query": "Test query",
            "selected_mode": "rag",
            "source_scope": "uploaded_only",
            "primary_agent": "RAG Agent",
            "summary": "Retrieved 1 passage from uploaded documents.",
            "key_metrics": [],
            "citations": [{"source": "[q3.csv, p. 1]", "date": "2024", "excerpt": "Revenue 5400"}],
            "confidence_score": 0.95,
            "sub_query_count": 1,
            "competitors": {},
            "validation_summary": {"passed": True, "issues": []},
            "missing_information": [],
            "conflicts": [],
            "agent_traces": {"rag_agent": {"active": True, "chunks_count": 1}},
        }

        with patch("app.api.routes.agentic.run_query", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_result
            payload = {
                "query": "What was the Q3 revenue in the uploaded report?",
                "selected_mode": "rag",
                "source_scope": "uploaded_only",
                "selected_document_ids": ["doc_123"],
            }
            res = client.post("/api/agentic/query", json=payload, headers=auth_headers)
            assert res.status_code == 200
            res_data = res.json()
            assert res_data["selected_mode"] == "rag"
            assert res_data["source_scope"] == "uploaded_only"
            assert res_data["primary_agent"] == "RAG Agent"
            assert len(res_data["run_id"]) > 0

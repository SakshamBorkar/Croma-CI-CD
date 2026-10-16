"""
app/api/routes/documents.py
───────────────────────────
FastAPI routes for user document management:
  - POST   /api/documents/upload   Upload single or multiple documents
  - GET    /api/documents          List uploaded documents for current user
  - GET    /api/documents/{id}     Retrieve metadata & processing status
  - DELETE /api/documents/{id}     Remove document, disk file, and ChromaDB chunks
  - GET    /api/documents/{id}/preview Retrieve document excerpt for citation preview
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from loguru import logger

from app.core.auth import UserContext, get_current_user
from app.ingestion.document_processor import (
    process_and_register_document,
    list_user_documents,
    get_user_document,
    delete_user_document,
    get_document_preview,
)

documents_router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size: int
    created_at: str
    status: str
    stage: str
    chunk_count: int
    page_count: int
    error_message: str | None = None


@documents_router.post("/upload", response_model=List[DocumentResponse])
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: UserContext = Depends(get_current_user),
) -> List[DocumentResponse]:
    """
    Upload and index one or more documents (PDF, Word, Text, CSV, Excel).
    Processes files asynchronously, generating semantic chunks and ChromaDB embeddings.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    responses: List[DocumentResponse] = []
    user_id = getattr(current_user, "email", None) or getattr(current_user, "username", "demo_user")

    for file in files:
        try:
            content = await file.read()
            record = await process_and_register_document(
                file_bytes=content,
                filename=file.filename or "uploaded_file",
                user_id=user_id,
            )
            responses.append(DocumentResponse(**record))
        except ValueError as ve:
            logger.warning(f"Validation error for {file.filename}: {ve}")
            responses.append(
                DocumentResponse(
                    document_id="invalid",
                    filename=file.filename or "unknown",
                    file_type="unknown",
                    file_size=0,
                    created_at="",
                    status="failed",
                    stage="validation",
                    chunk_count=0,
                    page_count=0,
                    error_message=str(ve),
                )
            )
        except Exception as e:
            logger.error(f"Processing error for {file.filename}: {e}")
            responses.append(
                DocumentResponse(
                    document_id="error",
                    filename=file.filename or "unknown",
                    file_type="unknown",
                    file_size=0,
                    created_at="",
                    status="failed",
                    stage="error",
                    chunk_count=0,
                    page_count=0,
                    error_message=f"Failed to process document: {str(e)}",
                )
            )

    return responses


@documents_router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    current_user: UserContext = Depends(get_current_user),
) -> List[DocumentResponse]:
    """List all documents uploaded by the current user."""
    user_id = getattr(current_user, "email", None) or getattr(current_user, "username", "demo_user")
    docs = list_user_documents(user_id)
    return [DocumentResponse(**d) for d in docs]


@documents_router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: UserContext = Depends(get_current_user),
) -> DocumentResponse:
    """Retrieve metadata and status for a specific document."""
    user_id = getattr(current_user, "email", None) or getattr(current_user, "username", "demo_user")
    doc = get_user_document(document_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentResponse(**doc)


@documents_router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a document, its disk file, and all associated ChromaDB chunks."""
    user_id = getattr(current_user, "email", None) or getattr(current_user, "username", "demo_user")
    success = delete_user_document(document_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found or unauthorized.")
    return {"status": "deleted", "document_id": document_id}


@documents_router.get("/{document_id}/preview")
async def preview_document(
    document_id: str,
    current_user: UserContext = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve document structure and text preview for citation inspection."""
    user_id = getattr(current_user, "email", None) or getattr(current_user, "username", "demo_user")
    preview = get_document_preview(document_id, user_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Document preview not available.")
    return preview

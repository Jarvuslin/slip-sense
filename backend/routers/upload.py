"""Upload router — file upload, Supabase Storage, and document classification."""

from __future__ import annotations

import os
import uuid
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from middleware.auth import get_current_user
from models.database import get_db
from models.schemas import DocumentResponse, UploadResponse
from models.tables import Document, DocumentStatus
from services.classifier import classify_file

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


def _get_supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    return create_client(url, key)


def _validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more tax documents. Each file is:
    1. Validated (type, size)
    2. Uploaded to Supabase Storage
    3. Classified via GPT-4o vision
    4. Recorded in the database
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    session_id = uuid.uuid4()
    documents: list[DocumentResponse] = []
    supabase = _get_supabase()

    for file in files:
        _validate_file(file)

        file_bytes = await file.read()
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB",
            )

        storage_path = f"{user_id}/{session_id}/{file.filename}"

        # Upload to Supabase Storage
        try:
            supabase.storage.from_("tax-documents").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": file.content_type or "application/octet-stream"},
            )
        except Exception as exc:
            logger.error("Storage upload failed for %s: %s", file.filename, exc)
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}")

        # Create document record
        doc = Document(
            user_id=user_id,
            session_id=session_id,
            filename=file.filename,
            storage_path=storage_path,
            status=DocumentStatus.CLASSIFYING.value,
        )
        db.add(doc)
        await db.flush()

        # Classify
        result = await classify_file(file_bytes, file.filename)

        doc.doc_type = result.doc_type.value
        doc.classification_confidence = result.confidence
        doc.tax_year = result.tax_year
        doc.status = (
            DocumentStatus.CLASSIFIED.value
            if result.confidence >= 0.8
            else DocumentStatus.NEEDS_CLASSIFICATION.value
        )

        documents.append(
            DocumentResponse(
                id=doc.id,
                session_id=session_id,
                filename=doc.filename,
                doc_type=doc.doc_type,
                classification_confidence=doc.classification_confidence,
                status=doc.status,
                tax_year=doc.tax_year,
                created_at=doc.created_at,
            )
        )

    await db.commit()

    return UploadResponse(session_id=session_id, documents=documents)


@router.put("/documents/{document_id}/classify")
async def correct_classification(
    document_id: uuid.UUID,
    doc_type: str,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Allow the user to manually correct a document's classification."""
    from sqlalchemy import select

    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    valid_types = {"T4", "T5", "T2202", "RRSP", "T4A", "T4E", "T3", "T5007", "DONATION"}
    if doc_type.upper() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid document type. Valid types: {', '.join(valid_types)}")

    doc.doc_type = doc_type.upper()
    doc.classification_confidence = 1.0
    doc.status = DocumentStatus.CLASSIFIED.value
    await db.commit()

    return {"message": "Classification updated", "doc_type": doc.doc_type}

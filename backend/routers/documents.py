"""Documents router — list, view extracted data, manage findings, delete sessions."""

from __future__ import annotations

import os
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from middleware.auth import get_current_user
from models.database import get_db
from models.schemas import DocumentResponse, FindingResponse
from models.tables import Document, ExtractedData, Finding, Report

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    return create_client(url, key)


@router.get("/sessions/{session_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    session_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents in a session."""
    result = await db.execute(
        select(Document).where(
            Document.session_id == session_id,
            Document.user_id == user_id,
        ).order_by(Document.created_at)
    )
    docs = result.scalars().all()
    return [
        DocumentResponse(
            id=d.id,
            session_id=d.session_id,
            filename=d.filename,
            doc_type=d.doc_type,
            classification_confidence=d.classification_confidence,
            status=d.status,
            tax_year=d.tax_year,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get("/documents/{document_id}/extracted")
async def get_extracted_data(
    document_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get extracted structured data for a specific document."""
    result = await db.execute(
        select(ExtractedData).where(
            ExtractedData.document_id == document_id,
            ExtractedData.user_id == user_id,
        )
    )
    extracted = result.scalar_one_or_none()
    if not extracted:
        raise HTTPException(status_code=404, detail="Extracted data not found")

    return {
        "id": str(extracted.id),
        "document_id": str(extracted.document_id),
        "data": extracted.data,
        "field_confidences": extracted.field_confidences,
        "created_at": extracted.created_at.isoformat(),
    }


class FindingUpdateRequest(BaseModel):
    reviewed: bool | None = None


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: uuid.UUID,
    body: FindingUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a finding as reviewed or not applicable."""
    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.user_id == user_id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if body.reviewed is not None:
        finding.reviewed = body.reviewed

    await db.flush()

    return FindingResponse(
        id=finding.id,
        session_id=finding.session_id,
        title=finding.title,
        description=finding.description,
        tier=finding.tier,
        confidence=finding.confidence,
        category=finding.category,
        source_document_id=finding.source_document_id,
        action_suggestion=finding.action_suggestion,
        why_it_matters=finding.why_it_matters,
        reviewed=finding.reviewed,
        source=finding.source,
        created_at=finding.created_at,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session and all associated data, including storage files."""
    # Get documents to find storage paths
    result = await db.execute(
        select(Document).where(
            Document.session_id == session_id,
            Document.user_id == user_id,
        )
    )
    docs = result.scalars().all()

    if not docs:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete from Supabase Storage
    supabase = _get_supabase()
    storage_paths = [d.storage_path for d in docs]
    try:
        supabase.storage.from_("tax-documents").remove(storage_paths)
    except Exception as exc:
        logger.warning("Failed to delete some storage files: %s", exc)

    # Cascade delete: findings, report, extracted_data, documents
    await db.execute(delete(Finding).where(Finding.session_id == session_id, Finding.user_id == user_id))
    await db.execute(delete(Report).where(Report.session_id == session_id, Report.user_id == user_id))

    doc_ids = [d.id for d in docs]
    await db.execute(delete(ExtractedData).where(ExtractedData.document_id.in_(doc_ids)))
    await db.execute(delete(Document).where(Document.session_id == session_id, Document.user_id == user_id))

    await db.commit()

    return {"message": "Session deleted", "documents_removed": len(docs)}

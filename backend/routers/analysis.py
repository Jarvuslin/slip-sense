"""Analysis router — trigger pipeline, stream progress via SSE, fetch reports."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from middleware.auth import get_current_user
from models.database import get_db
from models.schemas import FindingResponse, ReportResponse, DocumentResponse
from models.tables import Document, DocumentStatus, ExtractedData, Finding, Report
from services.extractor import extract_document
from services.analyzer import run_analysis
from services.reporter import generate_report

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_supabase():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    return create_client(url, key)


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/sessions/{session_id}/analyze")
async def analyze_session(
    session_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the full analysis pipeline for a session.

    Returns an SSE stream with progress updates through each stage:
    classifying -> extracting -> analyzing (rule_engine) -> analyzing (llm) -> complete
    """
    # Verify session exists and belongs to user
    result = await db.execute(
        select(Document).where(
            Document.session_id == session_id,
            Document.user_id == user_id,
        )
    )
    docs = result.scalars().all()
    if not docs:
        raise HTTPException(status_code=404, detail="Session not found or no documents")

    # Check for existing report
    existing = await db.execute(
        select(Report).where(Report.session_id == session_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Analysis already completed for this session")

    async def event_stream():
        supabase = _get_supabase()
        total = len(docs)
        extracted_documents = []

        # Stage 2: Extraction
        for i, doc in enumerate(docs):
            yield _sse_event({
                "stage": "extracting",
                "document": doc.filename,
                "progress": i + 1,
                "total": total,
            })

            # Download file from Supabase Storage
            try:
                file_response = supabase.storage.from_("tax-documents").download(doc.storage_path)
                file_bytes = file_response
            except Exception as exc:
                logger.error("Failed to download %s: %s", doc.storage_path, exc)
                doc.status = DocumentStatus.ERROR.value
                continue

            # Extract structured data
            doc.status = DocumentStatus.EXTRACTING.value
            data = await extract_document(file_bytes, doc.filename, doc.doc_type or "UNKNOWN")

            # Store extracted data
            extracted = ExtractedData(
                document_id=doc.id,
                user_id=user_id,
                data=data,
                field_confidences=data.get("field_confidences", {}),
            )
            db.add(extracted)
            doc.status = DocumentStatus.EXTRACTED.value

            extracted_documents.append({
                "document_id": str(doc.id),
                "doc_type": doc.doc_type,
                "filename": doc.filename,
                "data": data,
            })

        await db.flush()

        # Stage 3a: Rule engine
        yield _sse_event({"stage": "analyzing", "substage": "rule_engine"})

        # Stage 3b: LLM patterns
        yield _sse_event({"stage": "analyzing", "substage": "llm_patterns"})

        findings = await run_analysis(extracted_documents)

        # Stage 4: Report generation
        yield _sse_event({"stage": "reporting"})

        report = await generate_report(
            session_id=session_id,
            user_id=user_id,
            documents=extracted_documents,
            findings=findings,
            db=db,
        )

        await db.commit()

        yield _sse_event({
            "stage": "complete",
            "report_id": str(report.id),
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/report", response_model=ReportResponse)
async def get_report(
    session_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the completed analysis report for a session."""
    result = await db.execute(
        select(Report).where(
            Report.session_id == session_id,
            Report.user_id == user_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Fetch findings
    findings_result = await db.execute(
        select(Finding).where(
            Finding.session_id == session_id,
            Finding.user_id == user_id,
        ).order_by(Finding.tier, Finding.confidence.desc())
    )
    findings = findings_result.scalars().all()

    # Fetch documents
    docs_result = await db.execute(
        select(Document).where(
            Document.session_id == session_id,
            Document.user_id == user_id,
        )
    )
    documents = docs_result.scalars().all()

    return ReportResponse(
        id=report.id,
        session_id=report.session_id,
        summary=report.summary,
        total_income=report.total_income,
        total_tax_deducted=report.total_tax_deducted,
        document_count=report.document_count,
        findings_auto_verified=report.findings_auto_verified,
        findings_needs_review=report.findings_needs_review,
        findings_flagged=report.findings_flagged,
        findings=[
            FindingResponse(
                id=f.id,
                session_id=f.session_id,
                title=f.title,
                description=f.description,
                tier=f.tier,
                confidence=f.confidence,
                category=f.category,
                source_document_id=f.source_document_id,
                action_suggestion=f.action_suggestion,
                why_it_matters=f.why_it_matters,
                reviewed=f.reviewed,
                source=f.source,
                created_at=f.created_at,
            )
            for f in findings
        ],
        documents=[
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
            for d in documents
        ],
        created_at=report.created_at,
    )

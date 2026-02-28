"""Stage 4: Report generation — aggregate findings, compute summary, persist."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import FindingCreate, FindingTier
from models.tables import Finding, Report

logger = logging.getLogger(__name__)


async def generate_report(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    documents: list[dict],
    findings: list[FindingCreate],
    db: AsyncSession,
) -> Report:
    """Aggregate findings, compute summary stats, and persist everything.

    Args:
        session_id: The analysis session UUID
        user_id: The authenticated user's UUID
        documents: List of document dicts with extracted data
        findings: Combined findings from rule engine + LLM
        db: Async SQLAlchemy session
    """
    # Compute summary statistics
    total_income = 0.0
    total_tax_deducted = 0.0

    for doc in documents:
        data = doc.get("data", {})
        doc_type = doc.get("doc_type", "")

        if doc_type == "T4":
            total_income += data.get("employment_income") or 0
            total_tax_deducted += data.get("income_tax_deducted") or 0
        elif doc_type == "T5":
            total_income += (data.get("interest_income") or 0)
            total_income += (data.get("actual_dividends_eligible") or 0)
            total_income += (data.get("actual_dividends_other") or 0)

    # Count findings by tier
    counts = {tier: 0 for tier in FindingTier}
    for f in findings:
        counts[f.tier] = counts.get(f.tier, 0) + 1

    # Sort findings: flagged first, then needs_review, then auto_verified
    tier_order = {
        FindingTier.FLAGGED: 0,
        FindingTier.NEEDS_REVIEW: 1,
        FindingTier.AUTO_VERIFIED: 2,
    }
    sorted_findings = sorted(findings, key=lambda f: (tier_order.get(f.tier, 3), -f.confidence))

    # Persist findings
    finding_records = []
    for f in sorted_findings:
        record = Finding(
            session_id=session_id,
            user_id=user_id,
            title=f.title,
            description=f.description,
            tier=f.tier.value if isinstance(f.tier, FindingTier) else f.tier,
            confidence=f.confidence,
            category=f.category,
            source_document_id=uuid.UUID(f.source_document_id) if f.source_document_id else None,
            action_suggestion=f.action_suggestion,
            why_it_matters=f.why_it_matters,
            reviewed=False,
            source=f.source,
        )
        db.add(record)
        finding_records.append(record)

    # Build summary JSON
    summary = {
        "total_income": round(total_income, 2),
        "total_tax_deducted": round(total_tax_deducted, 2),
        "document_count": len(documents),
        "document_types": list({d.get("doc_type") for d in documents if d.get("doc_type")}),
        "findings_count": len(findings),
        "findings_by_source": {
            "rule_engine": len([f for f in findings if f.source == "rule_engine"]),
            "llm": len([f for f in findings if f.source == "llm"]),
        },
    }

    # Persist report
    report = Report(
        session_id=session_id,
        user_id=user_id,
        summary=summary,
        total_income=round(total_income, 2),
        total_tax_deducted=round(total_tax_deducted, 2),
        document_count=len(documents),
        findings_auto_verified=counts.get(FindingTier.AUTO_VERIFIED, 0),
        findings_needs_review=counts.get(FindingTier.NEEDS_REVIEW, 0),
        findings_flagged=counts.get(FindingTier.FLAGGED, 0),
    )
    db.add(report)
    await db.flush()

    logger.info(
        "Report generated for session %s: %d documents, %d findings "
        "(%d auto-verified, %d needs review, %d flagged)",
        session_id,
        len(documents),
        len(findings),
        counts.get(FindingTier.AUTO_VERIFIED, 0),
        counts.get(FindingTier.NEEDS_REVIEW, 0),
        counts.get(FindingTier.FLAGGED, 0),
    )

    return report

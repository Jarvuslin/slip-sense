"""Pydantic schemas for tax document types and API request/response models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DocType(str, Enum):
    T4 = "T4"
    T5 = "T5"
    T2202 = "T2202"
    RRSP = "RRSP"
    T4A = "T4A"
    T4E = "T4E"
    T3 = "T3"
    T5007 = "T5007"
    DONATION = "DONATION"
    UNKNOWN = "UNKNOWN"


class FindingTier(str, Enum):
    AUTO_VERIFIED = "auto_verified"
    NEEDS_REVIEW = "needs_review"
    FLAGGED = "flagged"


class DocumentStatus(str, Enum):
    UPLOADING = "uploading"
    CLASSIFYING = "classifying"
    CLASSIFIED = "classified"
    NEEDS_CLASSIFICATION = "needs_classification"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Tax document extraction schemas
# ---------------------------------------------------------------------------

class T4Data(BaseModel):
    """T4 – Statement of Remuneration Paid."""
    tax_year: int | None = None
    employer_name: str | None = None
    employer_address: str | None = None
    employee_name: str | None = None
    sin: str | None = None  # masked after validation
    employment_income: float | None = Field(None, description="Box 14")
    cpp_contributions: float | None = Field(None, description="Box 16")
    cpp2_contributions: float | None = Field(None, description="Box 16A – second CPP contributions")
    ei_premiums: float | None = Field(None, description="Box 18")
    income_tax_deducted: float | None = Field(None, description="Box 22")
    pension_adjustment: float | None = Field(None, description="Box 52")
    union_dues: float | None = Field(None, description="Box 44")
    charitable_donations: float | None = Field(None, description="Box 46")
    rpp_contributions: float | None = Field(None, description="Box 20")
    employment_code: str | None = Field(None, description="Box 29")
    field_confidences: dict[str, float] = Field(default_factory=dict)


class T5Data(BaseModel):
    """T5 – Statement of Investment Income."""
    tax_year: int | None = None
    payer_name: str | None = None
    recipient_name: str | None = None
    sin: str | None = None
    actual_dividends_eligible: float | None = Field(None, description="Box 10")
    actual_dividends_other: float | None = Field(None, description="Box 11")
    interest_income: float | None = Field(None, description="Box 13")
    capital_gains_dividends: float | None = Field(None, description="Box 18")
    foreign_income: float | None = Field(None, description="Box 15")
    taxable_dividends_eligible: float | None = Field(None, description="Box 24")
    taxable_dividends_other: float | None = Field(None, description="Box 25")
    dividend_tax_credit_eligible: float | None = Field(None, description="Box 26")
    field_confidences: dict[str, float] = Field(default_factory=dict)


class T2202Data(BaseModel):
    """T2202 – Tuition and Enrolment Certificate."""
    tax_year: int | None = None
    institution_name: str | None = None
    student_name: str | None = None
    sin: str | None = None
    tuition_fees_eligible: float | None = Field(None, description="Box A")
    months_part_time: int | None = Field(None, description="Box B – part-time months")
    months_full_time: int | None = Field(None, description="Box C – full-time months")
    field_confidences: dict[str, float] = Field(default_factory=dict)


class RRSPData(BaseModel):
    """RRSP Contribution Receipt."""
    tax_year: int | None = None
    issuer_name: str | None = None
    contributor_name: str | None = None
    sin: str | None = None
    contribution_amount: float | None = None
    contribution_date: str | None = None
    first_60_days: bool | None = Field(None, description="Whether contribution was in first 60 days of following year")
    field_confidences: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Classification result
# ---------------------------------------------------------------------------

class ClassificationResult(BaseModel):
    doc_type: DocType
    confidence: float = Field(ge=0.0, le=1.0)
    tax_year: int | None = None
    reasoning: str | None = None


# ---------------------------------------------------------------------------
# Finding schema
# ---------------------------------------------------------------------------

class FindingCreate(BaseModel):
    title: str
    description: str
    tier: FindingTier
    confidence: float = Field(ge=0.0, le=1.0)
    category: str
    source_document_id: uuid.UUID | None = None
    action_suggestion: str | None = None
    why_it_matters: str | None = None
    source: str = "rule_engine"


class FindingResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    description: str
    tier: FindingTier
    confidence: float
    category: str
    source_document_id: uuid.UUID | None = None
    action_suggestion: str | None = None
    why_it_matters: str | None = None
    reviewed: bool
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Document response
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    filename: str
    doc_type: str | None
    classification_confidence: float | None
    status: str
    tax_year: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Report response
# ---------------------------------------------------------------------------

class ReportResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    summary: dict
    total_income: float | None
    total_tax_deducted: float | None
    document_count: int
    findings_auto_verified: int
    findings_needs_review: int
    findings_flagged: int
    findings: list[FindingResponse] = []
    documents: list[DocumentResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Upload response
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    session_id: uuid.UUID
    documents: list[DocumentResponse]


# ---------------------------------------------------------------------------
# LLM structured output schemas (for OpenAI response_format)
# ---------------------------------------------------------------------------

class LLMFinding(BaseModel):
    """Schema for findings returned by the LLM analysis pass."""
    title: str
    description: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    action_suggestion: str | None = None
    why_it_matters: str | None = None


class LLMAnalysisResponse(BaseModel):
    """Schema for the full LLM analysis response."""
    findings: list[LLMFinding]
    summary_notes: str | None = None

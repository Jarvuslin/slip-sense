"""Stage 3: Hybrid analyzer — rule engine (pass 1) + LLM patterns (pass 2)."""

from __future__ import annotations

import logging
import uuid

from models.schemas import FindingCreate, FindingTier
from services.llm import analyze_patterns
from utils.tax_rules import (
    validate_cpp,
    validate_ei,
    check_tax_deducted_reasonableness,
    estimate_rrsp_room,
    detect_duplicate_employers,
    TAX_YEAR,
)

logger = logging.getLogger(__name__)


def _get_t4_list(documents: list[dict]) -> list[dict]:
    return [d["data"] for d in documents if d.get("doc_type") == "T4"]


def _get_t5_list(documents: list[dict]) -> list[dict]:
    return [d["data"] for d in documents if d.get("doc_type") == "T5"]


def _get_t2202_list(documents: list[dict]) -> list[dict]:
    return [d["data"] for d in documents if d.get("doc_type") == "T2202"]


def _get_rrsp_list(documents: list[dict]) -> list[dict]:
    return [d["data"] for d in documents if d.get("doc_type") == "RRSP"]


def _run_rule_engine(documents: list[dict]) -> list[FindingCreate]:
    """Pass 1: Deterministic rule-based checks."""
    findings: list[FindingCreate] = []

    t4s = _get_t4_list(documents)
    t5s = _get_t5_list(documents)
    t2202s = _get_t2202_list(documents)
    rrsps = _get_rrsp_list(documents)

    total_employment_income = 0.0
    total_tax_deducted = 0.0
    total_pension_adjustment = 0.0

    # --- T4 checks ---
    for i, t4 in enumerate(t4s):
        doc_id = documents[i].get("document_id") if i < len(documents) else None

        income = t4.get("employment_income") or 0
        total_employment_income += income
        total_tax_deducted += t4.get("income_tax_deducted") or 0
        total_pension_adjustment += t4.get("pension_adjustment") or 0

        # CPP validation
        cpp = t4.get("cpp_contributions")
        if cpp is not None and income:
            finding = validate_cpp(income, cpp, source_document_id=doc_id)
            if finding:
                findings.append(finding)

        # EI validation
        ei = t4.get("ei_premiums")
        if ei is not None and income:
            finding = validate_ei(income, ei, source_document_id=doc_id)
            if finding:
                findings.append(finding)

    # Duplicate employer check
    findings.extend(detect_duplicate_employers(t4s))

    # --- Aggregate income checks ---
    total_investment_income = 0.0
    for t5 in t5s:
        total_investment_income += (t5.get("interest_income") or 0)
        total_investment_income += (t5.get("actual_dividends_eligible") or 0)
        total_investment_income += (t5.get("actual_dividends_other") or 0)
        total_investment_income += (t5.get("capital_gains_dividends") or 0)

    total_income = total_employment_income + total_investment_income

    # Income verification finding
    if total_income > 0:
        findings.append(
            FindingCreate(
                title="Total Income Summary",
                description=(
                    f"Total employment income: ${total_employment_income:,.2f} "
                    f"(from {len(t4s)} T4{'s' if len(t4s) != 1 else ''}). "
                    f"Total investment income: ${total_investment_income:,.2f} "
                    f"(from {len(t5s)} T5{'s' if len(t5s) != 1 else ''}). "
                    f"Combined total: ${total_income:,.2f}."
                ),
                tier=FindingTier.AUTO_VERIFIED,
                confidence=0.90,
                category="income_summary",
                action_suggestion=None,
                why_it_matters="This is the total income that will be reported on your tax return.",
                source="rule_engine",
            )
        )

    # Tax deducted reasonableness
    if total_income > 0 and total_tax_deducted > 0:
        finding = check_tax_deducted_reasonableness(total_income, total_tax_deducted)
        if finding:
            findings.append(finding)

    # --- RRSP room estimation ---
    if total_employment_income > 0:
        estimated_room = estimate_rrsp_room(total_employment_income, total_pension_adjustment)
        total_rrsp_contributions = sum(
            (r.get("contribution_amount") or 0) for r in rrsps
        )

        if total_rrsp_contributions > 0:
            findings.append(
                FindingCreate(
                    title="RRSP Contribution Summary",
                    description=(
                        f"You contributed ${total_rrsp_contributions:,.2f} to your RRSP. "
                        f"Based on your income, your estimated new RRSP room for {TAX_YEAR} "
                        f"is approximately ${estimated_room:,.2f}. "
                        "Note: Your actual room depends on carry-forward from prior years — "
                        "check your CRA Notice of Assessment for the exact figure."
                    ),
                    tier=FindingTier.NEEDS_REVIEW,
                    confidence=0.70,
                    category="rrsp_analysis",
                    action_suggestion="Verify your RRSP contribution room against your latest CRA Notice of Assessment.",
                    why_it_matters="Over-contributing to your RRSP incurs a 1% per-month penalty on the excess.",
                    source="rule_engine",
                )
            )
        elif estimated_room > 1000:
            findings.append(
                FindingCreate(
                    title="No RRSP Contributions Detected",
                    description=(
                        f"No RRSP contribution receipts were uploaded. Based on your income "
                        f"of ${total_employment_income:,.2f}, your estimated new RRSP room "
                        f"is approximately ${estimated_room:,.2f}."
                    ),
                    tier=FindingTier.NEEDS_REVIEW,
                    confidence=0.65,
                    category="rrsp_analysis",
                    action_suggestion=(
                        "If you made RRSP contributions, upload the receipts. If not, "
                        "consider contributing before the deadline to reduce your tax owing."
                    ),
                    why_it_matters="RRSP contributions directly reduce your taxable income.",
                    source="rule_engine",
                )
            )

    # --- T2202 tuition check ---
    for t2202 in t2202s:
        tuition = t2202.get("tuition_fees_eligible") or 0
        months_ft = t2202.get("months_full_time") or 0
        months_pt = t2202.get("months_part_time") or 0

        if tuition > 0:
            findings.append(
                FindingCreate(
                    title="Tuition Credit Available",
                    description=(
                        f"You have eligible tuition fees of ${tuition:,.2f} "
                        f"({months_ft} full-time months, {months_pt} part-time months). "
                        "This qualifies for the federal tuition tax credit."
                    ),
                    tier=FindingTier.AUTO_VERIFIED,
                    confidence=0.90,
                    category="education_credits",
                    action_suggestion=(
                        "If you don't need the full credit to reduce your tax to zero, "
                        "you can transfer up to $5,000 to a parent/grandparent or carry it forward."
                    ),
                    why_it_matters="The tuition tax credit directly reduces your federal tax payable.",
                    source="rule_engine",
                )
            )

    return findings


async def run_analysis(documents: list[dict]) -> list[FindingCreate]:
    """Run the full hybrid analysis: rule engine + LLM pattern detection.

    Args:
        documents: List of dicts, each with keys: document_id, doc_type, data, filename
    """
    # Pass 1: Rule engine
    logger.info("Starting rule engine analysis on %d documents", len(documents))
    rule_findings = _run_rule_engine(documents)
    logger.info("Rule engine produced %d findings", len(rule_findings))

    # Build summary of rule findings for the LLM to avoid duplication
    rule_summary_lines = []
    for f in rule_findings:
        rule_summary_lines.append(f"- [{f.category}] {f.title}: {f.description[:200]}")
    rule_summary = "\n".join(rule_summary_lines) if rule_summary_lines else "No rule-based findings."

    # Pass 2: LLM pattern analysis
    extracted_data_for_llm = [
        {
            "doc_type": d.get("doc_type"),
            "filename": d.get("filename"),
            "data": d.get("data", {}),
        }
        for d in documents
    ]

    try:
        logger.info("Starting LLM pattern analysis")
        llm_response = await analyze_patterns(extracted_data_for_llm, rule_summary)

        llm_findings: list[FindingCreate] = []
        for lf in llm_response.findings:
            # Cap LLM confidence at 0.85
            capped_confidence = min(lf.confidence, 0.85)
            tier = (
                FindingTier.AUTO_VERIFIED if capped_confidence >= 0.85
                else FindingTier.NEEDS_REVIEW if capped_confidence >= 0.60
                else FindingTier.FLAGGED
            )
            llm_findings.append(
                FindingCreate(
                    title=lf.title,
                    description=lf.description,
                    tier=tier,
                    confidence=capped_confidence,
                    category=lf.category,
                    action_suggestion=lf.action_suggestion,
                    why_it_matters=lf.why_it_matters,
                    source="llm",
                )
            )
        logger.info("LLM analysis produced %d findings", len(llm_findings))
    except Exception as exc:
        logger.error("LLM analysis failed: %s", exc)
        llm_findings = [
            FindingCreate(
                title="AI Pattern Analysis Unavailable",
                description=(
                    "The AI-powered pattern analysis could not be completed. "
                    "Rule-based checks were still performed successfully."
                ),
                tier=FindingTier.NEEDS_REVIEW,
                confidence=0.50,
                category="system",
                action_suggestion="Try re-running the analysis. If the issue persists, review your documents manually.",
                why_it_matters="Some deduction opportunities may not have been identified.",
                source="llm",
            )
        ]

    # Merge both passes
    all_findings = rule_findings + llm_findings
    return all_findings

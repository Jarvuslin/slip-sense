"""Canadian tax rules and constants for the 2024 tax year.

All rule-based checks live here. These are deterministic — no LLM involved.
This is the first pass of the hybrid analyzer.
"""

from __future__ import annotations

from models.schemas import FindingCreate, FindingTier

TAX_YEAR = 2024

# --- CPP (Canada Pension Plan) ---
CPP_RATE = 0.0595
CPP_MAX_PENSIONABLE_EARNINGS = 68500
CPP_BASIC_EXEMPTION = 3500
CPP_MAX_EMPLOYEE_CONTRIBUTION = round(
    (CPP_MAX_PENSIONABLE_EARNINGS - CPP_BASIC_EXEMPTION) * CPP_RATE, 2
)  # $3,867.50

# CPP2 (second enhanced CPP — 2024 is first year)
CPP2_RATE = 0.04
CPP2_MAX_ADDITIONAL_EARNINGS = 73200
CPP2_MAX_EMPLOYEE_CONTRIBUTION = round(
    (CPP2_MAX_ADDITIONAL_EARNINGS - CPP_MAX_PENSIONABLE_EARNINGS) * CPP2_RATE, 2
)  # $188.00

# --- EI (Employment Insurance) ---
EI_RATE = 0.0166
EI_MAX_INSURABLE_EARNINGS = 63200
EI_MAX_PREMIUM = round(EI_MAX_INSURABLE_EARNINGS * EI_RATE, 2)  # $1,049.12

# --- Federal Tax Brackets (2024) ---
FEDERAL_BRACKETS: list[tuple[float, float]] = [
    (55867, 0.15),
    (55866, 0.205),
    (61942, 0.26),
    (36030, 0.29),
    (float("inf"), 0.33),
]
BASIC_PERSONAL_AMOUNT = 15705

# --- RRSP ---
RRSP_RATE = 0.18
RRSP_MAX_CONTRIBUTION_2024 = 31560

# Tolerance for comparing reported vs. expected values (5% or $50, whichever is larger)
_TOLERANCE_PCT = 0.05
_TOLERANCE_MIN = 50.0


def _within_tolerance(reported: float, expected: float) -> bool:
    tolerance = max(abs(expected) * _TOLERANCE_PCT, _TOLERANCE_MIN)
    return abs(reported - expected) <= tolerance


def validate_cpp(
    employment_income: float,
    reported_cpp: float,
    source_document_id: str | None = None,
) -> FindingCreate | None:
    """Check if reported CPP contributions match expected amount."""
    if employment_income <= CPP_BASIC_EXEMPTION:
        expected = 0.0
    elif employment_income >= CPP_MAX_PENSIONABLE_EARNINGS:
        expected = CPP_MAX_EMPLOYEE_CONTRIBUTION
    else:
        expected = round((employment_income - CPP_BASIC_EXEMPTION) * CPP_RATE, 2)

    if _within_tolerance(reported_cpp, expected):
        return FindingCreate(
            title="CPP Contributions Verified",
            description=(
                f"Your CPP contribution of ${reported_cpp:,.2f} is consistent with "
                f"employment income of ${employment_income:,.2f} "
                f"(expected ~${expected:,.2f})."
            ),
            tier=FindingTier.AUTO_VERIFIED,
            confidence=0.95,
            category="cpp_validation",
            source_document_id=source_document_id,
            action_suggestion=None,
            why_it_matters="CPP contributions are mandatory and should match the legislated rate.",
            source="rule_engine",
        )

    diff = reported_cpp - expected
    direction = "higher" if diff > 0 else "lower"
    return FindingCreate(
        title="CPP Contribution Discrepancy",
        description=(
            f"Your reported CPP contribution of ${reported_cpp:,.2f} is "
            f"${abs(diff):,.2f} {direction} than the expected "
            f"${expected:,.2f} based on your employment income of "
            f"${employment_income:,.2f}."
        ),
        tier=FindingTier.FLAGGED if abs(diff) > 200 else FindingTier.NEEDS_REVIEW,
        confidence=0.92,
        category="cpp_validation",
        source_document_id=source_document_id,
        action_suggestion="Compare this with your pay stubs. If the difference is significant, contact your employer or CRA.",
        why_it_matters="Incorrect CPP contributions could affect your CPP benefits in retirement and may indicate a payroll error.",
        source="rule_engine",
    )


def validate_ei(
    employment_income: float,
    reported_ei: float,
    source_document_id: str | None = None,
) -> FindingCreate | None:
    """Check if reported EI premiums match expected amount."""
    if employment_income >= EI_MAX_INSURABLE_EARNINGS:
        expected = EI_MAX_PREMIUM
    else:
        expected = round(employment_income * EI_RATE, 2)

    if _within_tolerance(reported_ei, expected):
        return FindingCreate(
            title="EI Premiums Verified",
            description=(
                f"Your EI premium of ${reported_ei:,.2f} is consistent with "
                f"employment income of ${employment_income:,.2f} "
                f"(expected ~${expected:,.2f})."
            ),
            tier=FindingTier.AUTO_VERIFIED,
            confidence=0.95,
            category="ei_validation",
            source_document_id=source_document_id,
            action_suggestion=None,
            why_it_matters="EI premiums fund your eligibility for Employment Insurance benefits.",
            source="rule_engine",
        )

    diff = reported_ei - expected
    direction = "higher" if diff > 0 else "lower"
    return FindingCreate(
        title="EI Premium Discrepancy",
        description=(
            f"Your reported EI premium of ${reported_ei:,.2f} is "
            f"${abs(diff):,.2f} {direction} than the expected "
            f"${expected:,.2f} based on your employment income of "
            f"${employment_income:,.2f}."
        ),
        tier=FindingTier.FLAGGED if abs(diff) > 100 else FindingTier.NEEDS_REVIEW,
        confidence=0.92,
        category="ei_validation",
        source_document_id=source_document_id,
        action_suggestion="Verify against your pay stubs. EI premiums are calculated at a fixed rate up to the annual maximum.",
        why_it_matters="Overpaid EI premiums may be refundable on your tax return. Underpaid premiums could indicate a payroll issue.",
        source="rule_engine",
    )


def estimate_federal_tax(taxable_income: float) -> float:
    """Estimate federal tax payable for a given taxable income."""
    remaining = max(taxable_income - BASIC_PERSONAL_AMOUNT, 0)
    tax = 0.0
    for bracket_size, rate in FEDERAL_BRACKETS:
        taxable_in_bracket = min(remaining, bracket_size)
        tax += taxable_in_bracket * rate
        remaining -= taxable_in_bracket
        if remaining <= 0:
            break
    return round(tax, 2)


def check_tax_deducted_reasonableness(
    total_income: float,
    tax_deducted: float,
    source_document_id: str | None = None,
) -> FindingCreate | None:
    """Check if income tax deducted is reasonable for the income level."""
    expected_federal = estimate_federal_tax(total_income)
    # Rough provincial estimate (~50% of federal as a ballpark)
    estimated_total_tax = expected_federal * 1.5
    effective_rate = tax_deducted / total_income if total_income > 0 else 0
    expected_rate = estimated_total_tax / total_income if total_income > 0 else 0

    if abs(effective_rate - expected_rate) < 0.08:
        return FindingCreate(
            title="Income Tax Deductions Appear Reasonable",
            description=(
                f"Your total income tax deducted of ${tax_deducted:,.2f} "
                f"({effective_rate:.1%} effective rate) appears reasonable for "
                f"your income level of ${total_income:,.2f}."
            ),
            tier=FindingTier.AUTO_VERIFIED,
            confidence=0.85,
            category="tax_deducted_check",
            source_document_id=source_document_id,
            action_suggestion=None,
            why_it_matters="Verifying that enough tax was deducted reduces the chance of owing a large balance at filing time.",
            source="rule_engine",
        )

    if effective_rate < expected_rate - 0.08:
        return FindingCreate(
            title="Income Tax Deducted May Be Low",
            description=(
                f"Your total income tax deducted of ${tax_deducted:,.2f} "
                f"({effective_rate:.1%} effective rate) appears lower than typical "
                f"for your income level. You may owe additional tax when filing."
            ),
            tier=FindingTier.NEEDS_REVIEW,
            confidence=0.75,
            category="tax_deducted_check",
            source_document_id=source_document_id,
            action_suggestion=(
                "This could be normal if you claimed additional deductions with your employer "
                "(e.g., RRSP, childcare). Verify with your pay stubs or CRA My Account."
            ),
            why_it_matters="Insufficient tax deductions during the year could lead to an unexpected tax bill.",
            source="rule_engine",
        )

    return FindingCreate(
        title="Income Tax Deducted Seems High",
        description=(
            f"Your total income tax deducted of ${tax_deducted:,.2f} "
            f"({effective_rate:.1%} effective rate) appears higher than typical "
            f"for your income level. You may be entitled to a refund."
        ),
        tier=FindingTier.NEEDS_REVIEW,
        confidence=0.75,
        category="tax_deducted_check",
        source_document_id=source_document_id,
        action_suggestion="This is not necessarily a problem — it may mean a larger refund. Review your deductions and credits.",
        why_it_matters="Over-withholding means you've been lending money to the government interest-free.",
        source="rule_engine",
    )


def estimate_rrsp_room(total_income: float, pension_adjustment: float = 0.0) -> float:
    """Estimate RRSP contribution room for the following year based on earned income.

    Note: Actual room also depends on carry-forward from prior years, which
    we don't have access to. This is an estimate for the current year's new room.
    """
    new_room = min(total_income * RRSP_RATE, RRSP_MAX_CONTRIBUTION_2024) - pension_adjustment
    return max(round(new_room, 2), 0)


def detect_duplicate_employers(t4_data_list: list[dict]) -> list[FindingCreate]:
    """Flag potential duplicate T4s from the same employer."""
    findings: list[FindingCreate] = []
    seen: dict[str, list[dict]] = {}

    for t4 in t4_data_list:
        name = (t4.get("employer_name") or "").strip().lower()
        if not name:
            continue
        seen.setdefault(name, []).append(t4)

    for name, entries in seen.items():
        if len(entries) > 1:
            total = sum(e.get("employment_income", 0) or 0 for e in entries)
            findings.append(
                FindingCreate(
                    title=f"Multiple T4s from '{entries[0].get('employer_name', name)}'",
                    description=(
                        f"Found {len(entries)} T4 slips from the same employer. "
                        f"Combined employment income: ${total:,.2f}. "
                        "This could be normal (e.g., amended slip or different pay types) "
                        "or could indicate a duplicate upload."
                    ),
                    tier=FindingTier.NEEDS_REVIEW,
                    confidence=0.80,
                    category="duplicate_detection",
                    action_suggestion="Check if these are duplicate uploads or legitimate separate T4s from the same employer.",
                    why_it_matters="Duplicate T4s could lead to over-reporting income on your tax return.",
                    source="rule_engine",
                )
            )

    return findings

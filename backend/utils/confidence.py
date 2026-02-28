"""Composable confidence scoring system.

Confidence is not a single number from the LLM — it's built from three
independent signals and combined with explicit weights.
"""

from __future__ import annotations

from models.schemas import FindingTier


# Weights for the composite score
W_EXTRACTION = 0.4
W_RULE = 0.3
W_CROSS_REF = 0.3

# Tier thresholds
TIER_AUTO_VERIFIED = 0.90
TIER_NEEDS_REVIEW = 0.60


def extraction_confidence(field_confidences: dict[str, float]) -> float:
    """Average of per-field confidence scores from LLM extraction.

    Returns 0.0 if no confidences are provided.
    """
    if not field_confidences:
        return 0.0
    values = [v for v in field_confidences.values() if isinstance(v, (int, float))]
    return sum(values) / len(values) if values else 0.0


def rule_confidence(passed: bool, deviation_pct: float = 0.0) -> float:
    """Score from the rule engine.

    - 1.0 if the check passes cleanly
    - Degrades proportionally to the deviation magnitude
    """
    if passed:
        return 1.0
    return max(0.0, 1.0 - abs(deviation_pct))


def cross_ref_confidence(agreement_scores: list[float]) -> float:
    """Agreement score across documents.

    Each score represents how well two documents agree on a shared value.
    Returns the average agreement, or 1.0 if no cross-references are applicable.
    """
    if not agreement_scores:
        return 1.0
    return sum(agreement_scores) / len(agreement_scores)


def overall_confidence(
    extraction: float,
    rule: float,
    cross_ref: float,
) -> float:
    """Weighted combination of the three confidence signals."""
    return round(
        W_EXTRACTION * extraction + W_RULE * rule + W_CROSS_REF * cross_ref,
        4,
    )


def confidence_to_tier(confidence: float) -> FindingTier:
    """Map an overall confidence score to a finding tier."""
    if confidence >= TIER_AUTO_VERIFIED:
        return FindingTier.AUTO_VERIFIED
    if confidence >= TIER_NEEDS_REVIEW:
        return FindingTier.NEEDS_REVIEW
    return FindingTier.FLAGGED

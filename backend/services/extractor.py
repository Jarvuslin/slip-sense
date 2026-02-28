"""Stage 2: Structured data extraction using GPT-4o with structured outputs."""

from __future__ import annotations

import base64
import io
import logging

from services.llm import extract_fields
from utils.validators import mask_sin_in_data, validate_sin, validate_tax_year

logger = logging.getLogger(__name__)


def _pdf_first_page_b64(file_bytes: bytes) -> str:
    """Convert PDF to base64 of first page image."""
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=200, fmt="png")
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return base64.b64encode(file_bytes).decode("utf-8")


async def extract_document(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
) -> dict:
    """Extract structured data from a classified tax document.

    Returns a dict with the extracted fields, field_confidences, and any
    validation flags.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        image_b64 = _pdf_first_page_b64(file_bytes)
    else:
        image_b64 = base64.b64encode(file_bytes).decode("utf-8")

    try:
        data = await extract_fields(image_b64, doc_type)
    except Exception as exc:
        logger.error("Extraction failed for %s: %s", filename, exc)
        return {
            "error": str(exc),
            "field_confidences": {},
            "_extraction_failed": True,
        }

    # Post-processing: SIN masking
    data = mask_sin_in_data(data)

    # Validate tax year
    tax_year = data.get("tax_year")
    if tax_year and not validate_tax_year(tax_year):
        data.setdefault("_warnings", []).append(
            f"Tax year {tax_year} does not match expected year 2024"
        )

    # Flag low-confidence fields
    field_confidences = data.get("field_confidences", {})
    low_confidence_fields = [
        field for field, conf in field_confidences.items()
        if isinstance(conf, (int, float)) and conf < 0.7
    ]
    if low_confidence_fields:
        data.setdefault("_warnings", []).append(
            f"Low confidence on fields: {', '.join(low_confidence_fields)}"
        )
        data["_needs_verification"] = True

    logger.info(
        "Extracted %d fields from %s (%s), %d low-confidence",
        len([k for k in data if not k.startswith("_")]),
        filename,
        doc_type,
        len(low_confidence_fields),
    )

    return data

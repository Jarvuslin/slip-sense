"""Stage 1: Document classification using GPT-4o vision."""

from __future__ import annotations

import base64
import io
import logging

from models.schemas import ClassificationResult, DocType
from services.llm import classify_document

logger = logging.getLogger(__name__)


def _pdf_to_images(file_bytes: bytes) -> list[bytes]:
    """Convert PDF bytes to a list of PNG image bytes (one per page)."""
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, dpi=200, fmt="png")
        result = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            result.append(buf.getvalue())
        return result
    except Exception as exc:
        logger.warning("pdf2image conversion failed: %s – trying raw bytes", exc)
        return [file_bytes]


def _detect_media_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "application/octet-stream"


async def classify_file(file_bytes: bytes, filename: str) -> ClassificationResult:
    """Classify a tax document file (PDF or image) into its type.

    For PDFs, converts the first page to an image and sends it to GPT-4o vision.
    Returns a ClassificationResult with doc_type, confidence, and optional reasoning.
    """
    media_type = _detect_media_type(filename)

    if media_type == "application/pdf":
        pages = _pdf_to_images(file_bytes)
        image_bytes = pages[0]  # classify based on first page
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    else:
        image_b64 = base64.b64encode(file_bytes).decode("utf-8")

    try:
        result = await classify_document(image_b64)
        logger.info(
            "Classified %s as %s (confidence: %.2f)",
            filename, result.doc_type, result.confidence,
        )
        return result
    except Exception as exc:
        logger.error("Classification failed for %s: %s", filename, exc)
        return ClassificationResult(
            doc_type=DocType.UNKNOWN,
            confidence=0.0,
            reasoning=f"Classification failed: {exc}",
        )

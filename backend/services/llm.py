"""Async OpenAI GPT-4o wrapper with structured outputs, retries, and token logging."""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

from openai import AsyncOpenAI, APIError, RateLimitError
import asyncio

from models.schemas import (
    ClassificationResult,
    LLMAnalysisResponse,
    T4Data,
    T5Data,
    T2202Data,
    RRSPData,
)
from prompts.classification import CLASSIFICATION_PROMPT
from prompts.extraction import get_extraction_prompt
from prompts.analysis import ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
MODEL = "gpt-4o"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0

_DOC_TYPE_TO_SCHEMA: dict[str, type] = {
    "T4": T4Data,
    "T5": T5Data,
    "T2202": T2202Data,
    "RRSP": RRSPData,
}


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _pydantic_to_json_schema(model_cls: type) -> dict[str, Any]:
    """Convert a Pydantic model to an OpenAI-compatible JSON schema."""
    schema = model_cls.model_json_schema()
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model_cls.__name__,
            "strict": False,
            "schema": schema,
        },
    }


async def _call_with_retry(
    messages: list[dict],
    response_format: dict | None = None,
    max_tokens: int = 4096,
) -> dict:
    """Call the OpenAI API with exponential backoff retry logic."""
    client = _get_client()

    for attempt in range(MAX_RETRIES):
        try:
            kwargs: dict[str, Any] = {
                "model": MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.1,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = await client.chat.completions.create(**kwargs)

            usage = response.usage
            if usage:
                logger.info(
                    "OpenAI tokens – prompt: %d, completion: %d, total: %d",
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                )

            content = response.choices[0].message.content
            return json.loads(content) if content else {}

        except RateLimitError:
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Rate limited, retrying in %.1fs (attempt %d/%d)", delay, attempt + 1, MAX_RETRIES)
            await asyncio.sleep(delay)
        except APIError as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("API error %s, retrying in %.1fs", exc, delay)
            await asyncio.sleep(delay)

    raise RuntimeError("Max retries exceeded for OpenAI API call")


def _image_message(image_base64: str, media_type: str = "image/png") -> dict:
    """Build a user message containing an image for GPT-4o vision."""
    return {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_base64}",
                    "detail": "high",
                },
            }
        ],
    }


async def classify_document(image_base64: str) -> ClassificationResult:
    """Classify a tax document image into its type."""
    messages = [
        {"role": "system", "content": CLASSIFICATION_PROMPT},
        _image_message(image_base64),
    ]
    response_format = _pydantic_to_json_schema(ClassificationResult)
    data = await _call_with_retry(messages, response_format=response_format)
    return ClassificationResult(**data)


async def extract_fields(image_base64: str, doc_type: str) -> dict:
    """Extract structured fields from a classified tax document image.

    Returns the raw dict so the caller can handle different doc types uniformly.
    """
    prompt = get_extraction_prompt(doc_type)
    schema_cls = _DOC_TYPE_TO_SCHEMA.get(doc_type)

    messages = [
        {"role": "system", "content": prompt},
        _image_message(image_base64),
    ]

    response_format = _pydantic_to_json_schema(schema_cls) if schema_cls else None
    data = await _call_with_retry(messages, response_format=response_format)
    return data


async def analyze_patterns(extracted_data_list: list[dict], rule_findings_summary: str) -> LLMAnalysisResponse:
    """Run the LLM pattern-analysis pass on all extracted data.

    The rule_findings_summary is a plain-text summary of what the rule engine
    already found, so the LLM can focus on what it hasn't covered.
    """
    user_content = (
        "## Extracted Tax Data\n\n"
        f"```json\n{json.dumps(extracted_data_list, indent=2, default=str)}\n```\n\n"
        "## Rule Engine Findings (already handled — do NOT duplicate these)\n\n"
        f"{rule_findings_summary}\n\n"
        "Analyze the data above and return your findings."
    )

    messages = [
        {"role": "system", "content": ANALYSIS_PROMPT},
        {"role": "user", "content": user_content},
    ]
    response_format = _pydantic_to_json_schema(LLMAnalysisResponse)
    data = await _call_with_retry(messages, response_format=response_format, max_tokens=8192)
    return LLMAnalysisResponse(**data)

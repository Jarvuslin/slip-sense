"""Field validation and SIN masking utilities."""

from __future__ import annotations

import re


def validate_sin(sin: str) -> bool:
    """Validate a Canadian Social Insurance Number using the Luhn algorithm.

    Accepts formats: 123456789 or 123-456-789
    """
    digits = re.sub(r"\D", "", sin)
    if len(digits) != 9:
        return False

    total = 0
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d

    return total % 10 == 0


def mask_sin(sin: str) -> str:
    """Mask a SIN, keeping only the last 3 digits.

    Returns format: ***-***-789
    """
    digits = re.sub(r"\D", "", sin)
    if len(digits) < 3:
        return "***-***-***"
    last3 = digits[-3:]
    return f"***-***-{last3}"


def is_numeric(value) -> bool:
    """Check if a value can be interpreted as a number."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value.replace(",", "").replace("$", "").strip())
            return True
        except (ValueError, AttributeError):
            return False
    return False


def parse_numeric(value) -> float | None:
    """Attempt to parse a value as a float, stripping common formatting."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").replace("$", "").strip())
        except (ValueError, AttributeError):
            return None
    return None


def validate_tax_year(year: int | None, expected: int = 2024) -> bool:
    """Check if the extracted tax year matches the expected year."""
    if year is None:
        return False
    return year == expected


def mask_sin_in_data(data: dict) -> dict:
    """Find and mask any SIN fields in a data dictionary (in-place + return)."""
    sin_keys = {"sin", "social_insurance_number", "SIN"}
    for key in sin_keys:
        if key in data and data[key]:
            raw = str(data[key])
            if validate_sin(raw):
                data[key] = mask_sin(raw)
            else:
                data[key] = mask_sin(raw)
    return data

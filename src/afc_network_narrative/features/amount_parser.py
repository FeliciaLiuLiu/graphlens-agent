from __future__ import annotations

import re

CURRENCY_MAP = {
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
}

UNKNOWN_AMOUNT_TEXT = {"", "unknown", "unreadable", "not visible", "n/a", "na", "none", "null"}


def parse_amount(amount_text: str | None) -> float | None:
    value, _currency = parse_amount_with_currency(amount_text)
    return value


def parse_amount_with_currency(amount_text: str | None) -> tuple[float | None, str | None]:
    if amount_text is None:
        return None, None

    text = amount_text.strip()
    if text.lower() in UNKNOWN_AMOUNT_TEXT:
        return None, None

    match = re.search(
        r"(?P<currency>\$|USD|EUR|GBP|€|£)?\s*(?P<number>\d[\d,]*(?:\.\d+)?)\s*(?P<suffix>[kKmMbB])?",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None, None

    number = float(match.group("number").replace(",", ""))
    suffix = (match.group("suffix") or "").lower()
    multiplier = {"": 1.0, "k": 1_000.0, "m": 1_000_000.0, "b": 1_000_000_000.0}[suffix]
    return number * multiplier, normalize_currency(match.group("currency"))


def normalize_currency(currency: str | None) -> str | None:
    if currency is None:
        return None
    stripped = currency.strip()
    if not stripped:
        return None
    return CURRENCY_MAP.get(stripped.lower(), CURRENCY_MAP.get(stripped, stripped.upper()))

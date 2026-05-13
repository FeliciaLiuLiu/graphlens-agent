from __future__ import annotations

from afc_network_narrative.features.amount_parser import parse_amount


def test_parse_amount_k_values() -> None:
    assert parse_amount("$10.0k") == 10000.0
    assert parse_amount("$1.7k") == 1700.0
    assert parse_amount("$2.7k") == 2700.0


def test_parse_amount_invalid() -> None:
    assert parse_amount("not visible") is None
    assert parse_amount("abc") is None

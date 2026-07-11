from __future__ import annotations

from sa_connector_sdk.normalize import content_hash, extract_gtin, normalize_text


def test_normalize_text__collapses_whitespace() -> None:
    assert normalize_text("  ASUS   TUF\tGAMING\n") == "ASUS TUF GAMING"


def test_normalize_text__empty_becomes_none() -> None:
    assert normalize_text("   ") is None
    assert normalize_text(None) is None


def test_extract_gtin__first_valid_wins() -> None:
    # invalid first, valid EAN-13 second
    assert extract_gtin(None, "not-a-gtin", "4711387781609") == "04711387781609"


def test_extract_gtin__none_when_all_invalid() -> None:
    assert extract_gtin(None, "", "123") is None


def test_content_hash__order_independent_and_change_sensitive() -> None:
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})
    assert content_hash({"a": 1}) != content_hash({"a": 2})

from __future__ import annotations

from sa_observability.sanitizer import REDACTED, redact, redacting_processor


def test_redact__top_level_sensitive_keys() -> None:
    out = redact({"password": "hunter2", "user": "alice"})
    assert out == {"password": REDACTED, "user": "alice"}


def test_redact__case_insensitive_and_substring() -> None:
    out = redact({"SID": "abc", "Authorization": "Bearer x", "X-Api-Key": "k"})
    assert out == {"SID": REDACTED, "Authorization": REDACTED, "X-Api-Key": REDACTED}


def test_redact__nested_and_lists() -> None:
    payload = {
        "account": {"id": "01J", "financial_terms": {"discount": 12}},
        "items": [{"session_id": "s1"}, {"session_id": "s2"}],
    }
    out = redact(payload)
    assert out["account"]["id"] == "01J"
    assert out["account"]["financial_terms"] == REDACTED
    # recurses into the list; each inner sensitive key is redacted
    assert out["items"] == [{"session_id": REDACTED}, {"session_id": REDACTED}]


def test_redact__collection_key_redacted_wholesale() -> None:
    # A key that itself names sensitive data (contains "session") is redacted entirely.
    out = redact({"sessions": [{"a": 1}]})
    assert out["sessions"] == REDACTED


def test_redact__non_sensitive_untouched() -> None:
    payload = {"offer_id": "01J", "price": "9900.00", "currency": "UAH"}
    assert redact(payload) == payload


def test_redact__short_marker_no_false_positive() -> None:
    # "sid" is a substring of "considered"/"outside" but only matches as a whole token.
    payload = {"considered": True, "outside_temp": 20, "sid": "leak-me"}
    out = redact(payload)
    assert out["considered"] is True
    assert out["outside_temp"] == 20
    assert out["sid"] == REDACTED


def test_redacting_processor__redacts_event_dict() -> None:
    processor = redacting_processor()
    result = processor(None, "info", {"event": "auth_ok", "token": "secret-token"})
    assert result == {"event": "auth_ok", "token": REDACTED}

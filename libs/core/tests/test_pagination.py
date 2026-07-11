from __future__ import annotations

import base64
import json

import pytest

from sa_core.errors import ValidationError
from sa_core.pagination import Page, decode_cursor, encode_cursor


def test_cursor__roundtrip() -> None:
    key = {"productID": 100463720, "id": "01J"}
    assert decode_cursor(encode_cursor(key)) == key


def test_cursor__is_opaque_urlsafe() -> None:
    cursor = encode_cursor({"id": "01J"})
    # url-safe base64: no padding-breaking characters that need escaping in a query string
    assert "/" not in cursor and "+" not in cursor


@pytest.mark.parametrize("bad", ["not-base64!!", "eyJub3QiOiJ", "AAAA"])
def test_decode_cursor__malformed__raises_validation_error(bad: str) -> None:
    with pytest.raises(ValidationError, match="malformed pagination cursor"):
        decode_cursor(bad)


def test_decode_cursor__non_object_payload__rejected() -> None:
    # A validly-encoded but non-dict payload (a JSON array) must still be rejected.
    cursor = base64.urlsafe_b64encode(json.dumps([1, 2, 3]).encode()).decode()
    with pytest.raises(ValidationError):
        decode_cursor(cursor)


def test_page__model_shape() -> None:
    page: Page[str] = Page(items=["a", "b"], next_cursor="abc", total_estimate=2)
    assert page.model_dump() == {
        "items": ["a", "b"],
        "next_cursor": "abc",
        "total_estimate": 2,
    }


def test_page__defaults() -> None:
    page: Page[int] = Page(items=[1])
    assert page.next_cursor is None
    assert page.total_estimate is None

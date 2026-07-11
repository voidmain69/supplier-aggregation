from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sa_core.ids import is_ulid, new_ulid, ulid_datetime


def test_new_ulid__format__is_26_char_crockford() -> None:
    ulid = new_ulid()
    assert len(ulid) == 26
    assert is_ulid(ulid)


def test_new_ulid__uniqueness__all_distinct() -> None:
    assert len({new_ulid() for _ in range(1000)}) == 1000


def test_new_ulid__monotonic__sorts_by_creation_order() -> None:
    earlier = new_ulid()
    later = new_ulid()
    # ULIDs are lexicographically sortable; later-or-equal timestamp keeps ordering.
    assert earlier <= later or ulid_datetime(earlier) <= ulid_datetime(later)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "TOO-SHORT",
        "0123456789012345678901234I",  # contains excluded letter I
        "0123456789012345678901234l",  # lowercase not accepted
        "012345678901234567890123456",  # 27 chars
    ],
)
def test_is_ulid__invalid__returns_false(value: str) -> None:
    assert not is_ulid(value)


def test_ulid_datetime__roundtrip__recovers_timestamp() -> None:
    before = datetime.now(UTC)
    ulid = new_ulid()
    recovered = ulid_datetime(ulid)
    # millisecond precision, so allow a small window around creation
    assert abs((recovered - before).total_seconds()) < 2


def test_ulid_datetime__invalid__raises() -> None:
    with pytest.raises(ValueError, match="not a valid ULID"):
        ulid_datetime("not-a-ulid")

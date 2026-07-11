from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from sa_core.time import ensure_utc, isoformat, utc_now


def test_utc_now__is_timezone_aware_utc() -> None:
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_ensure_utc__naive__rejected() -> None:
    with pytest.raises(ValueError, match="naive datetime"):
        ensure_utc(datetime(2026, 7, 11, 10, 0, 0))  # noqa: DTZ001 -- deliberately naive


def test_ensure_utc__converts_offset_to_utc() -> None:
    kyiv = timezone(timedelta(hours=3))
    value = datetime(2026, 7, 11, 13, 0, 0, tzinfo=kyiv)
    assert ensure_utc(value) == datetime(2026, 7, 11, 10, 0, 0, tzinfo=UTC)


def test_isoformat__emits_z_suffix() -> None:
    value = datetime(2026, 7, 11, 10, 0, 0, tzinfo=UTC)
    assert isoformat(value) == "2026-07-11T10:00:00Z"

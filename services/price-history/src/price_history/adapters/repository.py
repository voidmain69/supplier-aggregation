"""Data access for price points: append on ingest, range reads, and stats."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from price_history.adapters.models import EffectivePricePointRow, PricePointRow
from sa_contracts.events.offer_effective_price_changed import OfferEffectivePriceChanged
from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged
from sa_core.pagination import decode_cursor, encode_cursor
from sa_core.time import ensure_utc


def _decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


async def append_price_point(session: AsyncSession, data: SupplierOfferPriceChanged) -> None:
    """Append a price point (idempotent on the composite key ``(offer_id, ts)``)."""
    ts = ensure_utc(data.observed_at)
    existing = await session.get(PricePointRow, (data.offer_id, ts))
    if existing is not None:
        return
    session.add(
        PricePointRow(
            offer_id=data.offer_id,
            ts=ts,
            supplier_account_id=data.supplier_account_id,
            supplier_product_id=data.supplier_product_id,
            price=Decimal(data.new_price),
            currency=data.currency,
            price_uah=_decimal(data.price_uah),
        )
    )


async def append_effective_point(session: AsyncSession, data: OfferEffectivePriceChanged) -> None:
    """Append an effective-price point (idempotent on the composite key ``(offer_id, ts)``)."""
    ts = ensure_utc(data.observed_at)
    existing = await session.get(EffectivePricePointRow, (data.offer_id, ts))
    if existing is not None:
        return
    session.add(
        EffectivePricePointRow(
            offer_id=data.offer_id,
            ts=ts,
            supplier_account_id=data.supplier_account_id,
            supplier_product_id=data.supplier_product_id,
            effective_price_uah=Decimal(data.new_effective_price_uah),
            base_price=Decimal(data.base_price),
            currency=data.currency,
            cause=data.cause.value,
        )
    )


def _apply_range(
    stmt: Any, *, offer_id: str, from_ts: datetime | None, to_ts: datetime | None
) -> Any:
    stmt = stmt.where(PricePointRow.offer_id == offer_id)
    if from_ts is not None:
        stmt = stmt.where(PricePointRow.ts >= ensure_utc(from_ts))
    if to_ts is not None:
        stmt = stmt.where(PricePointRow.ts <= ensure_utc(to_ts))
    return stmt


async def list_price_points(
    session: AsyncSession,
    *,
    offer_id: str,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    cursor: str | None = None,
    limit: int = 100,
) -> tuple[Sequence[PricePointRow], str | None]:
    """Return price points for an offer, oldest first, cursor-paginated by timestamp."""
    stmt = (
        _apply_range(select(PricePointRow), offer_id=offer_id, from_ts=from_ts, to_ts=to_ts)
        .order_by(PricePointRow.ts)
        .limit(limit)
    )
    if cursor is not None:
        after = datetime.fromisoformat(str(decode_cursor(cursor)["after"]))
        if after.tzinfo is None:  # SQLite returns naive timestamps; treat them as UTC
            after = after.replace(tzinfo=UTC)
        stmt = stmt.where(PricePointRow.ts > after)
    rows = (await session.execute(stmt)).scalars().all()
    next_cursor = encode_cursor({"after": rows[-1].ts.isoformat()}) if len(rows) == limit else None
    return rows, next_cursor


async def price_stats(
    session: AsyncSession,
    *,
    offer_id: str,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> dict[str, Any]:
    """Aggregate UAH-price stats for an offer over a range (min/max/avg/last/count)."""
    agg = _apply_range(
        select(
            func.count().label("cnt"),
            func.min(PricePointRow.price_uah).label("min"),
            func.max(PricePointRow.price_uah).label("max"),
            func.avg(PricePointRow.price_uah).label("avg"),
        ),
        offer_id=offer_id,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    row = (await session.execute(agg)).one()

    last_stmt = (
        _apply_range(
            select(PricePointRow.price_uah, PricePointRow.ts),
            offer_id=offer_id,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        .order_by(PricePointRow.ts.desc())
        .limit(1)
    )
    last = (await session.execute(last_stmt)).first()

    def _str(value: Decimal | None) -> str | None:
        return f"{value:.4f}" if value is not None else None

    return {
        "offer_id": offer_id,
        "count": int(row.cnt),
        "min_uah": _str(row.min),
        "max_uah": _str(row.max),
        "avg_uah": _str(Decimal(row.avg) if row.avg is not None else None),
        "last_uah": _str(last.price_uah) if last is not None else None,
        "last_ts": last.ts.isoformat() if last is not None else None,
    }


async def daily_price_stats(
    session: AsyncSession,
    *,
    offer_id: str,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
) -> list[dict[str, Any]]:
    """Per-day UAH-price buckets for an offer (min/max/avg/last/count), oldest day first.

    A portable ``GROUP BY`` over the raw hypertable — correct on SQLite, Postgres and
    Timescale alike. In production the ``price_daily`` continuous aggregate materializes the
    same rollup for scale/BI (see the migration).
    """
    day = func.date(PricePointRow.ts)
    agg = (
        _apply_range(
            select(
                day.label("day"),
                func.count().label("cnt"),
                func.min(PricePointRow.price_uah).label("mn"),
                func.max(PricePointRow.price_uah).label("mx"),
                func.avg(PricePointRow.price_uah).label("av"),
            ),
            offer_id=offer_id,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        .group_by(day)
        .order_by(day)
    )
    agg_rows = (await session.execute(agg)).all()

    # Last price per day = the value at the latest ts within the day (one row per day).
    ranked = _apply_range(
        select(
            day.label("day"),
            PricePointRow.price_uah.label("last_uah"),
            func.row_number().over(partition_by=day, order_by=PricePointRow.ts.desc()).label("rn"),
        ),
        offer_id=offer_id,
        from_ts=from_ts,
        to_ts=to_ts,
    ).subquery()
    last_stmt = select(ranked.c.day, ranked.c.last_uah).where(ranked.c.rn == 1)
    last_by_day = {r.day: r.last_uah for r in (await session.execute(last_stmt)).all()}

    def _str(value: Decimal | None) -> str | None:
        return f"{value:.4f}" if value is not None else None

    return [
        {
            "day": str(r.day),
            "count": int(r.cnt),
            "min_uah": _str(r.mn),
            "max_uah": _str(r.mx),
            "avg_uah": _str(Decimal(r.av) if r.av is not None else None),
            "last_uah": _str(last_by_day.get(r.day)),
        }
        for r in agg_rows
    ]

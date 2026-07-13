"""Read API for price history — cursor-paginated points and range stats (AI-ready)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from price_history.adapters.repository import (
    daily_price_stats,
    list_price_points,
    price_stats,
)
from price_history.api.deps import get_session
from price_history.api.schemas import DailyPriceStatOut, PricePointOut, PriceStatsOut
from sa_core.pagination import Page

router = APIRouter(prefix="/v1", tags=["price-history"])

_OfferId = Annotated[str, Query(description="Offer id (ULID) to read the price history of.")]
_From = Annotated[
    datetime | None,
    Query(alias="from", description="Start of the range (ISO 8601 UTC), inclusive."),
]
_To = Annotated[
    datetime | None, Query(alias="to", description="End of the range (ISO 8601 UTC), inclusive.")
]


@router.get(
    "/price-history",
    operation_id="getPriceHistory",
    summary="List an offer's price history",
    description=(
        "Price points for an offer over an optional time range, oldest first. Cursor "
        "paginated. Use it to chart price movements or find when a price changed."
    ),
    response_model=Page[PricePointOut],
)
async def get_price_history(
    session: Annotated[AsyncSession, Depends(get_session)],
    offer_id: _OfferId,
    from_: _From = None,
    to: _To = None,
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=1000, description="Max points per page (1-1000, default 100).")
    ] = 100,
) -> Page[PricePointOut]:
    rows, next_cursor = await list_price_points(
        session, offer_id=offer_id, from_ts=from_, to_ts=to, cursor=cursor, limit=limit
    )
    return Page(items=[PricePointOut.from_row(r) for r in rows], next_cursor=next_cursor)


@router.get(
    "/price-history/stats",
    operation_id="getPriceStats",
    summary="Get price stats for an offer",
    description=(
        "Aggregate UAH-price statistics (min/max/avg/last and count) for an offer over an "
        "optional time range. Use it to judge whether the current price is good."
    ),
    response_model=PriceStatsOut,
)
async def get_price_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    offer_id: _OfferId,
    from_: _From = None,
    to: _To = None,
) -> PriceStatsOut:
    stats = await price_stats(session, offer_id=offer_id, from_ts=from_, to_ts=to)
    return PriceStatsOut(**stats)


@router.get(
    "/price-history/daily",
    operation_id="getPriceDaily",
    summary="Get an offer's daily price rollup",
    description=(
        "Per-day UAH-price buckets (min/max/avg/last and count) for an offer over an optional "
        "time range, oldest day first. Use it to chart a daily price trend."
    ),
    response_model=list[DailyPriceStatOut],
)
async def get_price_daily(
    session: Annotated[AsyncSession, Depends(get_session)],
    offer_id: _OfferId,
    from_: _From = None,
    to: _To = None,
) -> list[DailyPriceStatOut]:
    buckets = await daily_price_stats(session, offer_id=offer_id, from_ts=from_, to_ts=to)
    return [DailyPriceStatOut(**b) for b in buckets]

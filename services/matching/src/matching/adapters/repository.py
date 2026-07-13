"""Data access for canonical products and product links."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from matching.adapters.models import CanonicalProductRow, DecisionLogRow, ProductLinkRow
from matching.domain.embedding import cosine
from sa_core.ids import new_ulid
from sa_core.pagination import decode_cursor, encode_cursor
from sa_core.time import utc_now


def record_decision(
    session: AsyncSession,
    *,
    action: str,
    operator: str,
    canonical_product_id: str,
    supplier_product_id: str | None = None,
    method: str | None = None,
    confidence: float | None = None,
    note: str | None = None,
) -> DecisionLogRow:
    """Append an immutable audit record for a curation decision (app-minted ULID; not flushed)."""
    row = DecisionLogRow(
        decision_id=new_ulid(),
        action=action,
        operator=operator,
        canonical_product_id=canonical_product_id,
        supplier_product_id=supplier_product_id,
        method=method,
        confidence=confidence,
        note=note,
    )
    session.add(row)
    return row


@dataclass(frozen=True)
class CurationStats:
    """Aggregate counts for the operator dashboard."""

    pending_reviews: int
    canonical_products: int
    decisions_by_action: dict[str, int]


async def curation_stats(session: AsyncSession) -> CurationStats:
    """Counts for the dashboard: queue depth, canonical total, and decisions per action."""
    pending = await session.scalar(
        select(func.count())
        .select_from(ProductLinkRow)
        .where(ProductLinkRow.status == "pending_review")
    )
    canonical = await session.scalar(select(func.count()).select_from(CanonicalProductRow))
    action_rows = (
        await session.execute(
            select(DecisionLogRow.action, func.count()).group_by(DecisionLogRow.action)
        )
    ).all()
    return CurationStats(
        pending_reviews=pending or 0,
        canonical_products=canonical or 0,
        decisions_by_action={str(action): int(count) for action, count in action_rows},
    )


async def list_decisions(
    session: AsyncSession,
    *,
    supplier_product_id: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[Sequence[DecisionLogRow], str | None]:
    """The decision journal: curation decisions newest-first (ULID desc). Cursor-paged.

    Optionally filtered to one supplier product's history.
    """
    stmt = select(DecisionLogRow).order_by(DecisionLogRow.decision_id.desc()).limit(limit)
    if supplier_product_id is not None:
        stmt = stmt.where(DecisionLogRow.supplier_product_id == supplier_product_id)
    if cursor is not None:
        stmt = stmt.where(DecisionLogRow.decision_id < str(decode_cursor(cursor)["after"]))
    rows = (await session.execute(stmt)).scalars().all()
    next_cursor = encode_cursor({"after": rows[-1].decision_id}) if len(rows) == limit else None
    return rows, next_cursor


async def find_canonical_by_gtin(session: AsyncSession, gtin: str) -> CanonicalProductRow | None:
    stmt = select(CanonicalProductRow).where(CanonicalProductRow.gtin == gtin)
    return (await session.execute(stmt)).scalars().first()


async def get_canonical(
    session: AsyncSession, canonical_product_id: str
) -> CanonicalProductRow | None:
    return await session.get(CanonicalProductRow, canonical_product_id)


def create_canonical(
    session: AsyncSession,
    *,
    gtin: str | None,
    brand: str | None,
    title: str,
    status: str = "confirmed",
    embedding: list[float] | None = None,
) -> CanonicalProductRow:
    """Create a canonical product (app-minted ULID; not yet flushed)."""
    row = CanonicalProductRow(
        canonical_product_id=new_ulid(),
        gtin=gtin,
        brand=brand,
        title=title,
        status=status,
        embedding=embedding,
    )
    session.add(row)
    return row


async def nearest_canonical(
    session: AsyncSession,
    *,
    embedding: list[float],
    brand: str | None,
    limit: int = 20,
) -> tuple[CanonicalProductRow, float] | None:
    """The most similar existing canonical to ``embedding`` (cosine), or ``None``.

    On Postgres this is a pgvector nearest-neighbour search (``<=>``); on SQLite (unit tests)
    it falls back to computing cosine in Python over the bounded candidate set. Filtered by
    brand when known, so we never compare across brands.
    """
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        distance = CanonicalProductRow.embedding.cosine_distance(embedding)
        stmt = (
            select(CanonicalProductRow, distance.label("distance"))
            .where(CanonicalProductRow.embedding.is_not(None))
            .order_by(distance)
            .limit(1)
        )
        if brand is not None:
            stmt = stmt.where(CanonicalProductRow.brand == brand)
        row = (await session.execute(stmt)).first()
        if row is None:
            return None
        canonical, dist = row
        return canonical, 1.0 - float(dist)

    # SQLite / other: score the candidate set in Python.
    stmt = (
        select(CanonicalProductRow).where(CanonicalProductRow.embedding.is_not(None)).limit(limit)
    )
    if brand is not None:
        stmt = stmt.where(CanonicalProductRow.brand == brand)
    best: tuple[CanonicalProductRow, float] | None = None
    for candidate in (await session.execute(stmt)).scalars().all():
        score = cosine(embedding, list(candidate.embedding or []))
        if best is None or score > best[1]:
            best = (candidate, score)
    return best


def create_link(
    session: AsyncSession,
    *,
    supplier_product_id: str,
    canonical_product_id: str,
    method: str,
    confidence: float,
    status: str,
    decided_by: str,
) -> ProductLinkRow:
    """Create the link for a supplier product (called once per product; app-minted ids)."""
    row = ProductLinkRow(
        supplier_product_id=supplier_product_id,
        canonical_product_id=canonical_product_id,
        link_id=new_ulid(),
        method=method,
        confidence=confidence,
        status=status,
        decided_by=decided_by,
        decided_at=utc_now(),
    )
    session.add(row)
    return row


async def get_link(session: AsyncSession, supplier_product_id: str) -> ProductLinkRow | None:
    return await session.get(ProductLinkRow, supplier_product_id)


async def links_for_canonical(
    session: AsyncSession, canonical_product_id: str
) -> Sequence[ProductLinkRow]:
    """Every product link pointing at a canonical (used when merging two canonicals)."""
    stmt = select(ProductLinkRow).where(ProductLinkRow.canonical_product_id == canonical_product_id)
    return (await session.execute(stmt)).scalars().all()


async def delete_canonical(session: AsyncSession, row: CanonicalProductRow) -> None:
    """Remove a canonical product (e.g. the source side after a merge)."""
    await session.delete(row)


async def list_pending_links(
    session: AsyncSession, *, cursor: str | None = None, limit: int = 50
) -> tuple[Sequence[ProductLinkRow], str | None]:
    """The curation queue: links awaiting an operator decision, oldest first."""
    stmt = (
        select(ProductLinkRow)
        .where(ProductLinkRow.status == "pending_review")
        .order_by(ProductLinkRow.link_id)
        .limit(limit)
    )
    if cursor is not None:
        stmt = stmt.where(ProductLinkRow.link_id > str(decode_cursor(cursor)["after"]))
    rows = (await session.execute(stmt)).scalars().all()
    next_cursor = encode_cursor({"after": rows[-1].link_id}) if len(rows) == limit else None
    return rows, next_cursor


async def list_canonical(
    session: AsyncSession,
    *,
    gtin: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[Sequence[CanonicalProductRow], str | None]:
    stmt = (
        select(CanonicalProductRow).order_by(CanonicalProductRow.canonical_product_id).limit(limit)
    )
    if gtin is not None:
        stmt = stmt.where(CanonicalProductRow.gtin == gtin)
    if cursor is not None:
        stmt = stmt.where(
            CanonicalProductRow.canonical_product_id > str(decode_cursor(cursor)["after"])
        )
    rows = (await session.execute(stmt)).scalars().all()
    next_cursor = (
        encode_cursor({"after": rows[-1].canonical_product_id}) if len(rows) == limit else None
    )
    return rows, next_cursor

"""Canonical feedback on Postgres: link.confirmed -> canonical mapping. Integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from catalog.adapters.repository import canonical_ids_for
from catalog.events.handlers import build_discovered_handler, build_link_confirmed_handler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]
_SPID = "01J0000000000000000PROD1"
_CANON = "01J0000000000000000CAN01"


async def test_link_confirmed_sets_canonical_on_postgres(
    pg_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
    link_confirmed_event: Callable[..., dict[str, Any]],
) -> None:
    await build_discovered_handler(pg_session_factory)(discovered_event(supplier_product_id=_SPID))
    await build_link_confirmed_handler(pg_session_factory)(
        link_confirmed_event(supplier_product_id=_SPID, canonical_product_id=_CANON)
    )

    async with pg_session_factory() as session:
        assert await canonical_ids_for(session, [_SPID]) == {_SPID: _CANON}

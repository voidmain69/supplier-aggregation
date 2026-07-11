from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from connector_brain.adapters.brain_client import BrainClient, StaticCredentialResolver
from connector_brain.connector import BrainConnector
from connector_brain.db import create_schema
from connector_brain.settings import Settings
from sa_persistence.db import create_engine, create_session_factory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from sa_connector_sdk.dto import AccountCtx
from sa_connector_sdk.raw_archive import InMemoryRawArchive

SessionFactory = async_sessionmaker[AsyncSession]

FIXTURES = Path(__file__).parent / "fixtures" / "brain"

ACCOUNT = AccountCtx(
    account_id="acc1",
    supplier_code="brain",
    credentials_ref="vault/brain/acc1",
    settlement_currency="USD",
)


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def brain_fixtures() -> dict[str, Any]:
    return {
        "product": _load("product.json"),
        "categories": _load("categories.json"),
        "stocks": _load("stocks.json"),
        "modified": _load("modified.json"),
    }


class FakeBrain:
    """A scriptable Brain API backing an httpx.MockTransport.

    Records auth/GET calls so tests can assert SID reuse, retries and archiving.
    """

    def __init__(self, fixtures: dict[str, Any]) -> None:
        self._fixtures = fixtures
        self.auth_calls = 0
        self.get_calls: list[str] = []
        self.expire_session_once = False
        self._expired_used = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/auth":
            self.auth_calls += 1
            return httpx.Response(200, json={"status": 1, "result": f"SID-{self.auth_calls}"})

        self.get_calls.append(str(request.url))
        if path.startswith("/stocks/"):
            if self.expire_session_once and not self._expired_used:
                self._expired_used = True
                return httpx.Response(
                    200, json={"status": 0, "error": {"code": 102, "message": "session expired"}}
                )
            return httpx.Response(200, json={"status": 1, "result": self._fixtures["stocks"]})
        if path.startswith("/categories/"):
            return httpx.Response(200, json={"status": 1, "result": self._fixtures["categories"]})
        if path.startswith("/products/"):
            offset = int(request.url.params.get("offset", "0"))
            rows = [self._fixtures["product"]] if offset == 0 else []
            return httpx.Response(200, json={"status": 1, "result": rows})
        if path.startswith("/product/"):
            return httpx.Response(200, json={"status": 1, "result": self._fixtures["product"]})
        if "/modified_products" in path:
            offset = int(request.url.params.get("offset", "0"))
            rows = self._fixtures["modified"] if offset == 0 else []
            return httpx.Response(200, json={"status": 1, "result": rows})
        return httpx.Response(200, json={"status": 0, "error": {"code": 404, "message": "nf"}})


@pytest.fixture
def fake_brain(brain_fixtures: dict[str, Any]) -> FakeBrain:
    return FakeBrain(brain_fixtures)


@pytest.fixture
def account() -> AccountCtx:
    return ACCOUNT


@pytest.fixture
async def sqlite_session_factory() -> AsyncIterator[SessionFactory]:
    """Fresh in-memory SQLite with the service schema, for fast DB unit tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await create_schema(engine)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest.fixture
async def pg_session_factory() -> AsyncIterator[SessionFactory]:
    """The service schema on a real Postgres (testcontainers) — for @integration tests."""
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = re.sub(r"^postgresql\+?\w*", "postgresql+asyncpg", postgres.get_connection_url())
        engine = create_engine(dsn)
        await create_schema(engine)
        yield create_session_factory(engine)
        await engine.dispose()


ConnectorBuilder = Callable[..., tuple[BrainConnector, InMemoryRawArchive]]


@pytest.fixture
def build_connector(fake_brain: FakeBrain) -> ConnectorBuilder:
    """Return a factory: build a BrainConnector wired to the fake Brain over MockTransport."""

    def _make(
        *, page_size: int = 1, archive: InMemoryRawArchive | None = None
    ) -> tuple[BrainConnector, InMemoryRawArchive]:
        settings = Settings(page_size=page_size, requests_per_second=1000.0, env="dev")
        http = httpx.AsyncClient(
            base_url="http://api.brain.com.ua", transport=httpx.MockTransport(fake_brain.handler)
        )
        store = archive or InMemoryRawArchive()
        client = BrainClient(
            settings=settings,
            http=http,
            credentials=StaticCredentialResolver("login", "secret"),
            archive=store,
            account=ACCOUNT,
        )
        return BrainConnector(client=client, account=ACCOUNT, settings=settings), store

    return _make

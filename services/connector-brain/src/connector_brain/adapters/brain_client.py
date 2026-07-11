"""Low-level Brain HTTP client: auth/SID, rate limiting, raw archiving, error mapping.

Every call goes through the per-account rate bucket (3 req/s) and reuses a cached SID via
the session manager, re-authenticating once on a session-expired error. Raw responses are
archived before parsing (hard rule 9) — except the auth response, which carries the SID.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any, Protocol

import httpx

from connector_brain.settings import Settings
from sa_connector_sdk.dto import AccountCtx
from sa_connector_sdk.rate_limit import AsyncTokenBucket
from sa_connector_sdk.raw_archive import RawArchive
from sa_connector_sdk.session import SessionManager
from sa_core.errors import RateLimitedError, UpstreamError
from sa_core.ids import new_ulid

PathBuilder = Callable[[str], str]


class CredentialResolver(Protocol):
    """Resolves a Vault ``credentials_ref`` to (login, password). Secrets never persist."""

    async def resolve(self, credentials_ref: str) -> tuple[str, str]: ...


class StaticCredentialResolver:
    """Dev/test resolver holding a single login/password. Never use in production."""

    def __init__(self, login: str, password: str) -> None:
        self._login = login
        self._password = password

    async def resolve(self, credentials_ref: str) -> tuple[str, str]:
        return self._login, self._password


class BrainApiError(UpstreamError):
    """A Brain response with status != 1."""

    def __init__(self, code: int | None, message: str) -> None:
        super().__init__(f"Brain API error {code}: {message}", extra={"brain_error_code": code})
        self.brain_error_code = code


class BrainClient:
    """One client per supplier account (own SID, own rate budget)."""

    def __init__(
        self,
        *,
        settings: Settings,
        http: httpx.AsyncClient,
        credentials: CredentialResolver,
        archive: RawArchive,
        account: AccountCtx,
        rate: AsyncTokenBucket | None = None,
    ) -> None:
        self._settings = settings
        self._http = http
        self._credentials = credentials
        self._archive = archive
        self._account = account
        self._rate = rate or AsyncTokenBucket(rate=settings.requests_per_second)
        self._session = SessionManager(self._authenticate, ttl_seconds=settings.session_ttl_seconds)

    @staticmethod
    def _md5(password: str) -> str:
        return hashlib.md5(password.encode()).hexdigest()  # noqa: S324 -- Brain requires MD5

    @staticmethod
    def _error(payload: dict[str, Any]) -> tuple[int | None, str]:
        error = payload.get("error")
        if isinstance(error, dict):
            return error.get("code"), str(error.get("message", ""))
        return payload.get("error_code"), str(payload.get("error", "unknown error"))

    async def _archive_response(self, content: bytes) -> None:
        await self._archive.store(
            supplier_code=self._account.supplier_code,
            request_id=new_ulid(),
            payload=content,
        )

    async def _authenticate(self) -> str:
        login, password = await self._credentials.resolve(self._account.credentials_ref)
        await self._rate.acquire()
        resp = await self._http.post(
            "/auth", data={"login": login, "password": self._md5(password)}
        )
        payload = resp.json()
        if payload.get("status") == 1:
            return str(payload["result"])
        code, message = self._error(payload)
        raise BrainApiError(code, message or "authentication failed")

    async def _call(self, path: PathBuilder, *, params: dict[str, Any] | None = None) -> Any:
        for attempt in range(2):
            await self._rate.acquire()
            sid = await self._session.get()
            resp = await self._http.get(path(sid), params=params)
            await self._archive_response(resp.content)
            payload = resp.json()
            if payload.get("status") == 1:
                return payload["result"]
            code, message = self._error(payload)
            if attempt == 0 and code in self._settings.session_expired_codes:
                await self._session.invalidate()
                continue
            if code == self._settings.rate_limit_error_code:
                raise RateLimitedError(f"Brain rate limit hit: {message}")
            raise BrainApiError(code, message)
        raise BrainApiError(None, "session retry exhausted")

    async def get_categories(self) -> list[dict[str, Any]]:
        return await self._call(lambda sid: f"/categories/{sid}")

    async def get_products(
        self, category_id: str, *, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        return await self._call(
            lambda sid: f"/products/{category_id}/{sid}",
            params={"limit": limit, "offset": offset},
        )

    async def get_product_by_id(self, product_id: str) -> dict[str, Any]:
        return await self._call(lambda sid: f"/product/{product_id}/{sid}")

    async def get_product_by_articul(self, articul: str) -> dict[str, Any]:
        return await self._call(lambda sid: f"/product/articul/{articul}/{sid}")

    async def get_product_by_code(self, product_code: str) -> dict[str, Any]:
        return await self._call(lambda sid: f"/product/product_code/{product_code}/{sid}")

    async def get_stocks(self) -> list[dict[str, Any]]:
        return await self._call(lambda sid: f"/stocks/{sid}")

    async def get_modified_products(
        self, *, modified_type: str = "", modified_time: str, limit: int, offset: int
    ) -> list[Any]:
        def path(sid: str) -> str:
            if modified_type:
                return f"/modified_products/{modified_type}/{sid}"
            return f"/modified_products/{sid}"

        return await self._call(
            path, params={"modified_time": modified_time, "limit": limit, "offset": offset}
        )

"""FastAPI auth/authorization dependencies.

``require(scope)`` builds a dependency that (1) authenticates the bearer token, (2) checks
the principal holds the scope, and (3) applies the per-principal rate limit — raising the
matching ``sa_core`` error (401/403/429), which the shared handler renders as problem+json.
Rate limiting runs only after auth so anonymous floods can't exhaust a real principal's bucket.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request

from api_gateway.domain.auth import Principal, PrincipalStore, hash_token
from api_gateway.domain.rate_limit import RateLimiter
from sa_core.errors import ForbiddenError, RateLimitedError, UnauthorizedError

_BEARER = "bearer "


def _authenticate(request: Request) -> Principal:
    raw = request.headers.get("authorization")
    if raw is None or not raw.lower().startswith(_BEARER):
        raise UnauthorizedError("Provide a bearer token: `Authorization: Bearer <token>`.")
    token = raw[len(_BEARER) :].strip()
    if not token:
        raise UnauthorizedError("The bearer token is empty.")
    store: PrincipalStore = request.app.state.principals
    principal = store.resolve(hash_token(token))
    if principal is None:
        raise UnauthorizedError("The bearer token is not recognized or has been revoked.")
    return principal


def require(*scopes: str) -> Callable[[Request], Awaitable[Principal]]:
    """Build a dependency that authenticates, enforces ``scopes`` and rate-limits the caller."""

    async def dependency(request: Request) -> Principal:
        principal = _authenticate(request)
        for scope in scopes:
            if not principal.has(scope):
                raise ForbiddenError(f"This operation requires the `{scope}` scope.")
        limiter: RateLimiter = request.app.state.rate_limiter
        if not limiter.allow(principal.subject):
            raise RateLimitedError(
                "Rate limit exceeded for this principal; retry after the indicated delay.",
                retry_after_seconds=limiter.retry_after(principal.subject),
            )
        return principal

    return dependency

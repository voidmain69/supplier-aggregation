"""HTTP adapter for the internal services the gateway fronts.

The gateway reads/writes downstream services over HTTP (never their DB — hard rule 1). All
services already answer errors as RFC 9457 problem+json, so on a downstream 4xx/5xx the
gateway relays that body and status unchanged. A transport failure (service down, timeout)
becomes an :class:`~sa_core.errors.UpstreamError` (502).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from sa_core.errors import UpstreamError

# Logical service name -> whether it is reachable; base URLs are injected at construction.
Service = str


class Downstream:
    """Forwards requests to a named downstream service and returns the raw response."""

    def __init__(self, http: httpx.AsyncClient, base_urls: Mapping[Service, str]) -> None:
        self._http = http
        self._base_urls = {name: url.rstrip("/") for name, url in base_urls.items()}

    async def request(
        self,
        service: Service,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        base = self._base_urls[service]
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            return await self._http.request(method, f"{base}{path}", params=clean, json=json)
        except httpx.HTTPError as exc:
            raise UpstreamError(
                f"The {service} service is unreachable; retry shortly. ({exc})",
            ) from exc

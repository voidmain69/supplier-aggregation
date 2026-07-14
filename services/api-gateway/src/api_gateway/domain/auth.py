"""Authentication and authorization primitives (pure domain — no I/O, no framework).

A caller presents ``Authorization: Bearer <token>``. The gateway never stores raw tokens:
it hashes the presented token (SHA-256) and looks the hash up in a :class:`PrincipalStore`.
The resolved :class:`Principal` carries the scopes that gate each operation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol


class Scopes:
    """The platform's scope vocabulary (documented on every gated operation)."""

    CATALOG_READ = "catalog:read"
    OFFERS_READ = "offers:read"
    PRICES_READ = "prices:read"
    MATCHING_CURATE = "matching:curate"
    SEARCH_READ = "search:read"
    SYNC_READ = "sync:read"
    ACCOUNTS_FINANCIAL_READ = "accounts:financial:read"


@dataclass(frozen=True)
class Principal:
    """An authenticated caller and the scopes it holds."""

    subject: str
    scopes: frozenset[str]

    def has(self, scope: str) -> bool:
        return scope in self.scopes


def hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a bearer token (the store's lookup key)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class PrincipalStore(Protocol):
    """Resolves a token hash to a principal (or ``None`` if unknown)."""

    def resolve(self, token_hash: str) -> Principal | None: ...


class StaticPrincipalStore:
    """In-memory :class:`PrincipalStore` built from config (token hash -> principal)."""

    def __init__(self, principals: dict[str, Principal]) -> None:
        self._by_hash = principals

    def resolve(self, token_hash: str) -> Principal | None:
        return self._by_hash.get(token_hash)

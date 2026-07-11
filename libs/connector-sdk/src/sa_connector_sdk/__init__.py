"""sa_connector_sdk — the toolkit every supplier connector is built on.

Canonical DTOs, the :class:`SupplierConnector` protocol, an async token-bucket rate
limiter, a per-account session manager, normalization helpers, and a raw-payload archive.
Connectors depend on this; core services depend only on the protocol and DTOs.
"""

from __future__ import annotations

from sa_connector_sdk.dto import (
    AccountCtx,
    ConnectorHealth,
    DeltaRef,
    ProductRef,
    RawCategory,
    RawOffer,
    RawProduct,
    RawStock,
)
from sa_connector_sdk.normalize import content_hash, extract_gtin, normalize_text
from sa_connector_sdk.protocol import SupplierConnector
from sa_connector_sdk.rate_limit import AsyncTokenBucket
from sa_connector_sdk.raw_archive import InMemoryRawArchive, RawArchive, build_key
from sa_connector_sdk.session import SessionManager

__all__ = [
    "AccountCtx",
    "AsyncTokenBucket",
    "ConnectorHealth",
    "DeltaRef",
    "InMemoryRawArchive",
    "ProductRef",
    "RawArchive",
    "RawCategory",
    "RawOffer",
    "RawProduct",
    "RawStock",
    "SessionManager",
    "SupplierConnector",
    "build_key",
    "content_hash",
    "extract_gtin",
    "normalize_text",
]

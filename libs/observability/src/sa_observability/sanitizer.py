"""Secret redaction for logs (hard rule 6).

Never log supplier credentials, session ids (SIDs), tokens, or account financial terms.
This module redacts such fields structurally — by key name, recursively — so a stray
``log.info("auth_ok", sid=...)`` can't leak. Log structured fields (not sentences) and
this catches them; the default key set is extendable per service.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

REDACTED = "«redacted»"

# Field markers. Long markers (>=6 chars, normalized) match as a substring of the
# normalized key ("api_key" -> "apikey" matches "X-Api-Key"); short markers like "sid"
# match only as a whole token, so a benign key like "considered" is never redacted.
DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "sid",
        "session",
        "session_id",
        "credential",
        "authorization",
        "api_key",
        "apikey",
        "access_key",
        "private_key",
        "cookie",
        # account financial terms (not per-offer prices, which are legitimate telemetry)
        "financial_terms",
        "credit_limit",
        "payment_terms",
    }
)

_SEP = re.compile(r"[^A-Za-z0-9]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _tokens(key: str) -> set[str]:
    tokens: set[str] = set()
    for part in _SEP.split(key):
        tokens.update(tok.lower() for tok in _CAMEL.split(part) if tok)
    return tokens


def _normalized(key: str) -> str:
    return _SEP.sub("", key).lower()


def _is_sensitive(key: str, sensitive: Iterable[str]) -> bool:
    tokens = _tokens(key)
    normalized = _normalized(key)
    for marker in sensitive:
        norm_marker = _normalized(marker)
        if len(norm_marker) >= 6:
            if norm_marker in normalized:
                return True
        elif norm_marker in tokens:
            return True
    return False


def redact(value: Any, sensitive: Iterable[str] = DEFAULT_SENSITIVE_KEYS) -> Any:
    """Return a copy of ``value`` with sensitive fields replaced by a redaction marker.

    Recurses into dicts and lists; a dict entry is redacted when its key matches, so the
    whole subtree under a key like ``credentials`` disappears regardless of its shape.
    """
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive(str(key), sensitive) else redact(val, sensitive)
            for key, val in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, sensitive) for item in value]
    return value


def redacting_processor(
    sensitive: Iterable[str] = DEFAULT_SENSITIVE_KEYS,
) -> Any:
    """Build a structlog processor that redacts sensitive keys in each event dict."""
    markers = frozenset(sensitive)

    def processor(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        return redact(event_dict, markers)  # type: ignore[no-any-return]

    return processor

"""Pure query/text helpers for lexical search (no I/O, no framework).

Lexical matching is deliberately simple: a document's searchable text is the lowercased
concatenation of its name, brand, articul and codes; a query is tokenized the same way and
every token must appear (AND). PostgreSQL FTS ranking is a later refinement — see the README.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens of ``text`` (drops punctuation and whitespace)."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def document_text(*parts: str | None) -> str:
    """Build a document's searchable text from its fields (lowercased, space-joined)."""
    return " ".join(tokenize(" ".join(p for p in parts if p)))

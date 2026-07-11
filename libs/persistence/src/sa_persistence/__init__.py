"""sa_persistence — async SQLAlchemy wiring and the transactional outbox.

Services build tables on :class:`Base`, stage events with :func:`enqueue` inside their
business transaction, and run an :class:`OutboxRelay` to publish them exactly where they
were committed — the transactional-outbox pattern (hard rule 3).
"""

from __future__ import annotations

from sa_persistence.db import Base, create_all, create_engine, create_session_factory
from sa_persistence.outbox import OutboxRow, enqueue, fetch_unsent, mark_sent
from sa_persistence.relay import InMemoryPublisher, OutboxRelay, Publisher

__all__ = [
    "Base",
    "InMemoryPublisher",
    "OutboxRelay",
    "OutboxRow",
    "Publisher",
    "create_all",
    "create_engine",
    "create_session_factory",
    "enqueue",
    "fetch_unsent",
    "mark_sent",
]

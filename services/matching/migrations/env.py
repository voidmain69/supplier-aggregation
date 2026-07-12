"""Alembic environment for the matching service.

Thin wrapper: import this service's models so their tables register on the shared
``Base.metadata``, then hand off to the shared async runner. The DSN is read from the
service settings (env-overridable), so ``alembic upgrade head`` targets whichever database
the service is configured for.
"""

from __future__ import annotations

from matching.adapters import models as _models  # noqa: F401  (register tables on Base.metadata)
from matching.settings import Settings
from sa_persistence import outbox as _outbox  # noqa: F401  (register outbox table)
from sa_persistence.db import Base
from sa_persistence.migrate import run_migrations

run_migrations(Settings().db_dsn, Base.metadata)

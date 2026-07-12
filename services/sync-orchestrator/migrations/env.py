"""Alembic environment for the sync-orchestrator service.

Thin wrapper: import this service's models so their tables register on the shared
``Base.metadata``, then hand off to the shared async runner. The DSN is read from the
service settings (env-overridable), so ``alembic upgrade head`` targets whichever database
the service is configured for.
"""

from __future__ import annotations

from sa_persistence.db import Base
from sa_persistence.migrate import run_migrations
from sync_orchestrator.adapters import models as _models  # noqa: F401  (register tables)
from sync_orchestrator.settings import Settings

run_migrations(Settings().db_dsn, Base.metadata)

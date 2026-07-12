"""Alembic support shared by every service's ``migrations/env.py``.

Each service owns its database, so each keeps its own migration lineage — but they all run
through this one async-aware runner so ``env.py`` stays a few lines. The service passes its
async DSN (from its settings, env-overridable) and the ``Base.metadata`` populated by
importing that service's models; this handles both offline (``--sql``) and online modes.
"""

from __future__ import annotations

import asyncio

from alembic import context
from sqlalchemy import MetaData, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine


def _configure_and_run(connection: Connection, target_metadata: MetaData) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_online(url: str, target_metadata: MetaData) -> None:
    engine = create_async_engine(url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_configure_and_run, target_metadata)
    finally:
        await engine.dispose()


def run_migrations(url: str, target_metadata: MetaData) -> None:
    """Run Alembic migrations for ``url`` against ``target_metadata`` (offline or online)."""
    if context.is_offline_mode():
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        asyncio.run(_run_online(url, target_metadata))

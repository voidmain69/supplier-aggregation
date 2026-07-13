"""Sync monitoring API — account status + manual trigger (AI-ready, problem+json errors).

Read-only status for the operator dashboard, and a manual ``trigger`` that emits the same
``sync.job.requested`` the scheduler does (via the outbox). Exposes operational fields only —
never credentials or financial terms (hard rule 6). Auth/scopes come with the API gateway.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession

from sa_core.errors import NotFoundError
from sa_core.ids import new_ulid
from sa_core.time import utc_now
from sync_orchestrator.adapters.repository import load_last_requested, mark_requested
from sync_orchestrator.api.deps import get_session, get_settings
from sync_orchestrator.api.schemas import Problem, SyncAccountOut, TriggerResultOut
from sync_orchestrator.events.mapping import sync_requested_record
from sync_orchestrator.settings import Settings

router = APIRouter(prefix="/v1/sync", tags=["sync"])

_NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "No scheduled account with that id."}
}


@router.get(
    "/accounts",
    operation_id="listSyncAccounts",
    summary="List sync status per account",
    description=(
        "Every scheduled account and its sync health: last requested, next due and a derived "
        "status (never / ok / overdue). Operational fields only — no credentials or financial "
        "terms. Use it to monitor ingestion freshness."
    ),
    response_model=list[SyncAccountOut],
)
async def list_accounts(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SyncAccountOut]:
    last = await load_last_requested(session)
    now = utc_now()
    accounts = []
    for account in settings.accounts:
        last_at = last.get(account.account_id)
        next_due = last_at + timedelta(seconds=account.interval_seconds) if last_at else None
        if last_at is None:
            status = "never"
        elif next_due is not None and now >= next_due:
            status = "overdue"
        else:
            status = "ok"
        accounts.append(
            SyncAccountOut(
                account_id=account.account_id,
                supplier_code=account.supplier_code,
                kind=account.kind,
                mode=account.mode,
                interval_seconds=account.interval_seconds,
                last_requested_at=last_at.isoformat() if last_at else None,
                next_due_at=next_due.isoformat() if next_due else None,
                status=status,
            )
        )
    return accounts


@router.post(
    "/accounts/{account_id}/trigger",
    operation_id="triggerSync",
    summary="Request a sync now",
    description=(
        "Manually request a sync for an account — emits sync.job.requested (the same event the "
        "scheduler emits) so the account's connector fetches fresh data immediately. Returns the "
        "job id."
    ),
    response_model=TriggerResultOut,
    responses=_NOT_FOUND,
)
async def trigger_sync(
    account_id: Annotated[str, Path(description="Account id (ULID) to sync now.")],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TriggerResultOut:
    schedule = next((s for s in settings.schedules() if s.account_id == account_id), None)
    if schedule is None:
        raise NotFoundError(
            f"No scheduled account with id {account_id}.",
            instance=f"/v1/sync/accounts/{account_id}/trigger",
        )
    now = utc_now()
    job_id = new_ulid()
    enqueue(session, sync_requested_record(schedule, sync_job_id=job_id, requested_at=now))
    await mark_requested(session, account_id, now)
    await session.commit()
    return TriggerResultOut(account_id=account_id, sync_job_id=job_id, requested_at=now.isoformat())

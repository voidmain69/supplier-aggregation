"""Map a due account to a ``sync.job.requested`` outbox record."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sa_contracts import EVENT_REGISTRY
from sa_contracts.events.sync_job_requested import SyncJobRequested
from sa_core.events import OutboxRecord, make_cloud_event
from sync_orchestrator.domain.schedule import AccountSchedule

_SOURCE = "//sa/sync-orchestrator"
_TYPE = "sync.job.requested"


def sync_requested_record(
    schedule: AccountSchedule, *, sync_job_id: str, requested_at: datetime
) -> OutboxRecord:
    """Build the outbox record asking the account's connector to sync. Keyed by account_id."""
    payload: dict[str, Any] = SyncJobRequested(
        schema_version=1,
        supplier_code=schedule.supplier_code,
        account_id=schedule.account_id,
        credentials_ref=schedule.credentials_ref,
        settlement_currency=schedule.settlement_currency,
        kind=schedule.kind,  # a string; validated against the Kind enum
        sync_job_id=sync_job_id,
        requested_at=requested_at,
    ).model_dump(mode="json")

    spec = EVENT_REGISTRY[_TYPE]
    envelope = make_cloud_event(
        type=spec.event_type,
        source=_SOURCE,
        subject=schedule.account_id,
        dataschema=spec.dataschema,
        data=payload,
    )
    return OutboxRecord.for_event(topic=spec.topic, envelope=envelope)

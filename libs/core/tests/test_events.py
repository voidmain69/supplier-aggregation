from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema.validators import Draft202012Validator

from sa_core.events import OutboxRecord, make_cloud_event
from sa_core.ids import is_ulid

REPO_ROOT = Path(__file__).resolve().parents[3]
ENVELOPE_SCHEMA = json.loads(
    (REPO_ROOT / "contracts" / "events" / "_envelope.json").read_text(encoding="utf-8")
)


@pytest.fixture
def event() -> dict[str, Any]:
    return make_cloud_event(
        type="supplier.offer.price-changed",
        source="//sa/connector-brain",
        subject="01J000000000000000000OFFER",
        dataschema="https://contracts.sa.internal/events/supplier.offer.price-changed.json",
        data={"offer_id": "01J000000000000000000OFFER", "new_price": "9900.0000"},
        traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    )


def test_make_cloud_event__validates_against_envelope_schema(event: dict[str, Any]) -> None:
    Draft202012Validator(ENVELOPE_SCHEMA).validate(event)


def test_make_cloud_event__core_fields(event: dict[str, Any]) -> None:
    assert event["specversion"] == "1.0"
    assert is_ulid(event["id"])
    assert event["time"].endswith("Z")
    assert event["source"] == "//sa/connector-brain"


def test_make_cloud_event__traceparent_optional() -> None:
    event = make_cloud_event(
        type="supplier.offer.stock-changed",
        source="//sa/connector-brain",
        subject="01J000000000000000000OFFER",
        dataschema="https://contracts.sa.internal/events/supplier.offer.stock-changed.json",
        data={"offer_id": "01J000000000000000000OFFER"},
    )
    assert "traceparent" not in event
    Draft202012Validator(ENVELOPE_SCHEMA).validate(event)


def test_outbox_record__for_event__keys_by_subject(event: dict[str, Any]) -> None:
    record = OutboxRecord.for_event(topic="sa.supplier.offer", envelope=event)
    assert record.topic == "sa.supplier.offer"
    assert record.key == event["subject"]
    assert record.id == event["id"]
    assert record.envelope == event


def test_outbox_record__is_frozen(event: dict[str, Any]) -> None:
    record = OutboxRecord.for_event(topic="sa.supplier.offer", envelope=event)
    with pytest.raises(Exception, match=r"frozen|Instance is frozen"):
        record.topic = "other"  # type: ignore[misc]

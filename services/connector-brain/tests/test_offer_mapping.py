from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from connector_brain.events.mapping import offer_price_changed_record
from jsonschema.validators import Draft202012Validator

from sa_connector_sdk.dto import RawOffer
from sa_core.money import Money

REPO_ROOT = Path(__file__).resolve().parents[3]
ENVELOPE_SCHEMA = json.loads(
    (REPO_ROOT / "contracts" / "events" / "_envelope.json").read_text(encoding="utf-8")
)
OFFER_SCHEMA = json.loads(
    (REPO_ROOT / "contracts" / "events" / "supplier.offer.price-changed.json").read_text(
        encoding="utf-8"
    )
)

_OFFER = RawOffer(
    external_id="100463720",
    price=Money.of("222.22", "USD"),
    price_uah=Decimal("9900.00"),
    rrp=Money.of("9999.00", "UAH"),
    observed_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
)


def test_offer_record__envelope_and_payload_valid() -> None:
    record = offer_price_changed_record(
        _OFFER,
        offer_id="01J0000000000000000OFFER1",
        supplier_account_id="01J0000000000000000ACCT1",
        supplier_product_id="01J0000000000000000PROD1",
        old_price="200.0000",
        sync_job_id="01J0000000000000000SYNC1",
    )

    assert record.topic == "sa.supplier.offer"
    assert record.key == "01J0000000000000000OFFER1"  # keyed by offer_id
    Draft202012Validator(ENVELOPE_SCHEMA).validate(record.envelope)
    Draft202012Validator(OFFER_SCHEMA).validate(record.envelope["data"])


def test_offer_record__maps_prices() -> None:
    data = offer_price_changed_record(
        _OFFER,
        offer_id="01J0000000000000000OFFER1",
        supplier_account_id="01J0000000000000000ACCT1",
        supplier_product_id="01J0000000000000000PROD1",
        old_price=None,
        sync_job_id="01J0000000000000000SYNC1",
    ).envelope["data"]

    assert data["new_price"] == "222.2200"
    assert data["currency"] == "USD"
    assert data["price_uah"] == "9900.0000"
    assert data["rrp_uah"] == "9999.0000"
    assert data["old_price"] is None

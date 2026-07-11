from __future__ import annotations

import json
from pathlib import Path

from connector_brain.events.mapping import product_discovered_record
from jsonschema.validators import Draft202012Validator

from sa_connector_sdk.dto import RawProduct

REPO_ROOT = Path(__file__).resolve().parents[3]
ENVELOPE_SCHEMA = json.loads(
    (REPO_ROOT / "contracts" / "events" / "_envelope.json").read_text(encoding="utf-8")
)
PRODUCT_SCHEMA = json.loads(
    (REPO_ROOT / "contracts" / "events" / "supplier.product.discovered.json").read_text(
        encoding="utf-8"
    )
)

_PRODUCT = RawProduct(
    external_id="100463720",
    external_code="U1005797",
    name="ASUS TUF GAMING B850-PLUS WIFI",
    brand="ASUS",
    gtin="04711387781609",
    attributes={"Socket": "AM5"},
    supplier_category_id="1264",
)


def test_product_discovered_record__envelope_and_payload_valid() -> None:
    record = product_discovered_record(
        _PRODUCT,
        supplier_product_id="01J0000000000000000PROD01",
        supplier_code="brain",
        sync_job_id="01J0000000000000000SYNC01",
    )

    assert record.topic == "sa.supplier.product"
    assert record.key == "01J0000000000000000PROD01"  # keyed by supplier_product_id

    Draft202012Validator(ENVELOPE_SCHEMA).validate(record.envelope)
    Draft202012Validator(PRODUCT_SCHEMA).validate(record.envelope["data"])


def test_product_discovered_record__maps_fields() -> None:
    data = product_discovered_record(
        _PRODUCT,
        supplier_product_id="01J0000000000000000PROD01",
        supplier_code="brain",
        sync_job_id="01J0000000000000000SYNC01",
    ).envelope["data"]

    assert data["supplier_product_id"] == "01J0000000000000000PROD01"
    assert data["external_id"] == "100463720"
    assert data["gtin"] == "04711387781609"
    assert data["brand"] == "ASUS"
    assert data["attributes"] == {"Socket": "AM5"}

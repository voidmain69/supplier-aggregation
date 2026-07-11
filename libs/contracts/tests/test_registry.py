from __future__ import annotations

import pytest

from sa_contracts import EVENT_REGISTRY, spec_for
from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged


def test_registry__keys_are_event_types() -> None:
    assert "supplier.offer.price-changed" in EVENT_REGISTRY
    assert "matching.link.confirmed" in EVENT_REGISTRY
    assert "supplier.product.discovered" in EVENT_REGISTRY


def test_registry__topic_and_dataschema_derived_correctly() -> None:
    spec = spec_for("supplier.offer.price-changed")
    assert spec.model is SupplierOfferPriceChanged
    assert spec.topic == "sa.supplier.offer"
    assert spec.dataschema.endswith("/supplier.offer.price-changed.json")


def test_registry__type_field_matches_key() -> None:
    for event_type, spec in EVENT_REGISTRY.items():
        assert spec.event_type == event_type


def test_spec_for__unknown_type__raises() -> None:
    with pytest.raises(KeyError):
        spec_for("does.not.exist")


def test_model__validates_good_payload_and_rejects_float_price() -> None:
    good = SupplierOfferPriceChanged(
        schema_version=1,
        offer_id="01J000000000000000000OFFER",
        supplier_account_id="01J000000000000000000ACCT",
        supplier_product_id="01J000000000000000000PROD",
        new_price="9900.0000",
        currency="UAH",
        observed_at="2026-07-11T10:00:00Z",
        sync_job_id="01J000000000000000000SYNC",
    )
    assert good.new_price == "9900.0000"

    with pytest.raises(ValueError, match="new_price"):
        SupplierOfferPriceChanged(
            schema_version=1,
            offer_id="01J000000000000000000OFFER",
            supplier_account_id="01J000000000000000000ACCT",
            supplier_product_id="01J000000000000000000PROD",
            new_price="not-a-decimal-string",
            currency="UAH",
            observed_at="2026-07-11T10:00:00Z",
            sync_job_id="01J000000000000000000SYNC",
        )

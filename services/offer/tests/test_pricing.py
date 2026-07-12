"""Unit tests for the pricing engine (pure Decimal arithmetic)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from offer.domain.pricing import DEFAULT_TERMS, FinancialTerms, effective_price_uah


def test_effective__uah_default_terms__equals_base() -> None:
    price = effective_price_uah(base_price=Decimal("100"), currency="UAH", terms=DEFAULT_TERMS)
    assert price == Decimal("100.0000")


def test_effective__discount_and_markup_applied_in_order() -> None:
    terms = FinancialTerms(discount_pct=Decimal("0.10"), markup_pct=Decimal("0.05"))
    # 1000 * 0.90 * 1.05 = 945
    price = effective_price_uah(base_price=Decimal("1000"), currency="UAH", terms=terms)
    assert price == Decimal("945.0000")


def test_effective__non_uah_uses_fx_rate() -> None:
    terms = FinancialTerms(fx_rate_to_uah=Decimal("41.5"))
    # 10 USD * 41.5 = 415 UAH
    price = effective_price_uah(base_price=Decimal("10"), currency="USD", terms=terms)
    assert price == Decimal("415.0000")


def test_effective__non_uah_no_fx__falls_back_to_supplier_price_uah() -> None:
    price = effective_price_uah(
        base_price=Decimal("10"),
        currency="USD",
        terms=DEFAULT_TERMS,
        supplier_price_uah=Decimal("420"),
    )
    assert price == Decimal("420.0000")


def test_effective__non_uah_no_fx_no_supplier_uah__returns_none() -> None:
    assert (
        effective_price_uah(base_price=Decimal("10"), currency="USD", terms=DEFAULT_TERMS) is None
    )


def test_effective__uah_ignores_fx_rate() -> None:
    terms = FinancialTerms(fx_rate_to_uah=Decimal("41.5"))
    price = effective_price_uah(base_price=Decimal("100"), currency="UAH", terms=terms)
    assert price == Decimal("100.0000")


def test_effective__quantized_to_four_dp() -> None:
    terms = FinancialTerms(discount_pct=Decimal("0.333"))
    price = effective_price_uah(base_price=Decimal("99.99"), currency="UAH", terms=terms)
    assert price is not None
    assert price.as_tuple().exponent == -4


@pytest.mark.parametrize(
    "kwargs",
    [
        {"discount_pct": Decimal("1")},
        {"discount_pct": Decimal("-0.1")},
        {"markup_pct": Decimal("-0.1")},
        {"fx_rate_to_uah": Decimal("0")},
    ],
)
def test_financial_terms__invalid__rejected(kwargs: dict[str, Decimal]) -> None:
    with pytest.raises(ValueError, match="must be"):
        FinancialTerms(**kwargs)

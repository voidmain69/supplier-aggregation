from __future__ import annotations

from decimal import Decimal

import pytest

from sa_core.money import Money


def test_money__float_amount__rejected() -> None:
    with pytest.raises(ValueError, match="must not be a float"):
        Money(amount=9.99, currency="UAH")  # type: ignore[arg-type]


def test_money__string_and_int__accepted_and_scaled() -> None:
    assert Money.of("9900", "UAH").amount == Decimal("9900.0000")
    assert Money.of(5, "USD").amount == Decimal("5.0000")


def test_money__invalid_currency__rejected() -> None:
    with pytest.raises(ValueError, match="ISO-4217"):
        Money.of("1", "uah")
    with pytest.raises(ValueError, match="ISO-4217"):
        Money.of("1", "EURO")


def test_money__too_many_decimals__rejected() -> None:
    with pytest.raises(ValueError, match="4 decimal places"):
        Money.of("1.23456", "UAH")


def test_money__non_finite__rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        Money(amount=Decimal("NaN"), currency="UAH")


def test_money__add_sub__same_currency() -> None:
    total = Money.of("100.00", "UAH") + Money.of("0.50", "UAH")
    assert total.amount == Decimal("100.5000")
    assert (total - Money.of("0.50", "UAH")).amount == Decimal("100.0000")


def test_money__currency_mismatch__raises() -> None:
    with pytest.raises(ValueError, match="currency mismatch"):
        Money.of("1", "UAH") + Money.of("1", "USD")


def test_money__multiply_by_quantity() -> None:
    assert (Money.of("222.22", "USD") * 3).amount == Decimal("666.6600")
    with pytest.raises(TypeError, match="float"):
        Money.of("1", "USD") * 1.5  # type: ignore[operator]


def test_money__is_frozen() -> None:
    money = Money.of("1", "UAH")
    with pytest.raises(Exception, match=r"frozen|Instance is frozen"):
        money.amount = Decimal("2")  # type: ignore[misc]


def test_money__serializes_amount_as_string() -> None:
    dumped = Money.of("9900", "UAH").model_dump()
    assert dumped == {"amount": "9900.0000", "currency": "UAH"}

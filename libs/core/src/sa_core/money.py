"""Money value object: Decimal amount + ISO-4217 currency.

Hard rule: money is Decimal + ISO-4217 code, never float. Float amounts are rejected
at construction so a rounding bug can never enter the system silently. Arithmetic is
currency-safe: mixing currencies raises rather than producing a nonsense total.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_SCALE = Decimal("0.0001")  # 4 dp — matches NUMERIC(14,4) storage and the API string format


class Money(BaseModel):
    """An immutable monetary amount in a single currency."""

    model_config = ConfigDict(frozen=True)

    amount: Decimal
    currency: str

    @field_validator("amount", mode="before")
    @classmethod
    def _reject_float(cls, value: Any) -> Any:
        # A float has already lost precision; forbid it outright (bool is an int subclass, allow).
        if isinstance(value, float):
            raise ValueError("money amount must not be a float; use Decimal or a string")
        return value

    @field_validator("amount")
    @classmethod
    def _finite_and_scaled(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("money amount must be finite")
        # Reject rather than silently round away precision the caller sent.
        exponent = value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -4:
            raise ValueError(f"money amount has more than 4 decimal places: {value}")
        return value.quantize(_SCALE)

    @field_validator("currency")
    @classmethod
    def _valid_currency(cls, value: str) -> str:
        if not _CURRENCY_RE.match(value):
            raise ValueError(f"currency must be an ISO-4217 alpha code, got {value!r}")
        return value

    @field_serializer("amount")
    def _serialize_amount(self, value: Decimal) -> str:
        # API contract: amount is a string to preserve precision across JSON.
        return str(value)

    @classmethod
    def of(cls, amount: Decimal | int | str, currency: str) -> Money:
        """Construct Money from a Decimal, int, or decimal string (never a float)."""
        return cls(amount=Decimal(amount), currency=currency)

    def _check_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"currency mismatch: {self.currency} vs {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._check_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_same_currency(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, quantity: int | Decimal) -> Money:
        if isinstance(quantity, float):
            raise TypeError("cannot multiply Money by a float; use int or Decimal")
        return Money(amount=self.amount * Decimal(quantity), currency=self.currency)

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

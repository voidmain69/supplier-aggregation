"""Pricing engine: turn a supplier's base price into a comparable effective UAH price.

The platform holds one offer per (account x product); accounts differ in financial terms
(negotiated discount, settlement currency / FX, platform markup). The *effective price* folds
those terms into a single UAH figure so offers from different accounts and suppliers can be
ranked against each other — "where is this product really cheapest".

Pure domain: no I/O, only Decimal arithmetic (hard rules 2 and 4). Financial terms are
sensitive (hard rule 6) — this module computes with them but never logs them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

_UAH = "UAH"
_SCALE = Decimal("0.0001")  # 4 dp — matches NUMERIC(14,4) storage
_ONE = Decimal(1)


@dataclass(frozen=True)
class FinancialTerms:
    """An account's financial terms applied to every base price it produces.

    ``discount_pct``/``markup_pct`` are fractions (0.15 == 15%). ``fx_rate_to_uah`` converts the
    account's settlement currency to UAH; it is unused for UAH accounts and may be None when the
    rate is not configured (the engine then falls back to a supplier-provided UAH price).
    """

    discount_pct: Decimal = Decimal(0)
    markup_pct: Decimal = Decimal(0)
    fx_rate_to_uah: Decimal | None = None

    def __post_init__(self) -> None:
        if not (Decimal(0) <= self.discount_pct < _ONE):
            raise ValueError(f"discount_pct must be in [0, 1), got {self.discount_pct}")
        if self.markup_pct < Decimal(0):
            raise ValueError(f"markup_pct must be >= 0, got {self.markup_pct}")
        if self.fx_rate_to_uah is not None and self.fx_rate_to_uah <= Decimal(0):
            raise ValueError(f"fx_rate_to_uah must be > 0, got {self.fx_rate_to_uah}")


DEFAULT_TERMS = FinancialTerms()


def _base_in_uah(
    base_price: Decimal,
    currency: str,
    terms: FinancialTerms,
    supplier_price_uah: Decimal | None,
) -> Decimal | None:
    """Convert the base price to UAH, or None if no rate is available for a non-UAH currency."""
    if currency == _UAH:
        return base_price
    if terms.fx_rate_to_uah is not None:
        return base_price * terms.fx_rate_to_uah
    return supplier_price_uah  # supplier-supplied UAH price is the last-resort rate


def effective_price_uah(
    *,
    base_price: Decimal,
    currency: str,
    terms: FinancialTerms = DEFAULT_TERMS,
    supplier_price_uah: Decimal | None = None,
) -> Decimal | None:
    """Effective UAH price = UAH base, less discount, plus markup. None if it can't be priced.

    Returns None only when the currency is not UAH, no FX rate is configured, and the supplier
    gave no UAH price — i.e. there is genuinely no way to express the price in UAH yet.
    """
    uah_base = _base_in_uah(base_price, currency, terms, supplier_price_uah)
    if uah_base is None:
        return None
    effective = uah_base * (_ONE - terms.discount_pct) * (_ONE + terms.markup_pct)
    return effective.quantize(_SCALE)

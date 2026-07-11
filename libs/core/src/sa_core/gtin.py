"""GTIN normalization (hard rule 5).

EAN-13, UPC-A, EAN-8 and GTIN-14 are all the same identifier space at different widths.
Always normalize to GTIN-14 (left-padded, checksum-verified) via this module before
comparing or storing an identifier — otherwise the same product read from two suppliers
would look like two different GTINs.
"""

from __future__ import annotations

_VALID_LENGTHS = {8, 12, 13, 14}


def compute_check_digit(payload: str) -> int:
    """Compute the GS1 mod-10 check digit for a digit string without its check digit.

    Weights alternate 3 and 1 from the rightmost payload digit leftwards.
    """
    if not payload.isdigit():
        raise ValueError(f"payload must be digits only, got {payload!r}")
    total = 0
    for position, char in enumerate(reversed(payload)):
        weight = 3 if position % 2 == 0 else 1
        total += int(char) * weight
    return (10 - (total % 10)) % 10


def normalize_gtin(raw: str | int | None) -> str | None:
    """Normalize an EAN/UPC/GTIN to a 14-digit checksum-valid GTIN.

    Returns the GTIN-14 string, or None if the input is empty, not a supported width,
    or fails its check digit. Callers store/compare only the returned value; invalid
    inputs are kept elsewhere as raw_identifiers and never auto-matched.
    """
    if raw is None:
        return None
    digits = str(raw).strip()
    if not digits.isdigit() or len(digits) not in _VALID_LENGTHS:
        return None
    if compute_check_digit(digits[:-1]) != int(digits[-1]):
        return None
    return digits.zfill(14)


def is_valid_gtin(raw: str | int | None) -> bool:
    """Return True if the input normalizes to a valid GTIN-14."""
    return normalize_gtin(raw) is not None

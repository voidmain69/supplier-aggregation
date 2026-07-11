from __future__ import annotations

import pytest

from sa_core.gtin import compute_check_digit, is_valid_gtin, normalize_gtin


def test_compute_check_digit__known_ean13() -> None:
    # Real EAN from the Brain catalog sample (ASUS TUF GAMING B850-PLUS WIFI).
    assert compute_check_digit("471138778160") == 9


def test_compute_check_digit__non_digits__raises() -> None:
    with pytest.raises(ValueError, match="digits only"):
        compute_check_digit("47A138")


def test_normalize_gtin__ean13__padded_to_14() -> None:
    assert normalize_gtin("4711387781609") == "04711387781609"


def test_normalize_gtin__accepts_int_and_whitespace() -> None:
    assert normalize_gtin(" 4711387781609 ") == "04711387781609"
    assert normalize_gtin(4711387781609) == "04711387781609"


def test_normalize_gtin__upc_a_12_digits() -> None:
    # 036000291452 is the canonical UPC-A textbook example.
    assert normalize_gtin("036000291452") == "00036000291452"


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "12345",  # unsupported width
        "4711387781608",  # wrong check digit
        "abcdefghijklm",  # not digits
    ],
)
def test_normalize_gtin__invalid__returns_none(value: str | None) -> None:
    assert normalize_gtin(value) is None


def test_is_valid_gtin() -> None:
    assert is_valid_gtin("4711387781609")
    assert not is_valid_gtin("4711387781608")

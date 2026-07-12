from __future__ import annotations

from matching.domain.similarity import similarity


def test_identical_names_same_brand__near_one() -> None:
    score = similarity("ASUS TUF B850", "ASUS", "ASUS TUF B850", "ASUS")
    assert score == 1.0


def test_brand_mismatch__penalized() -> None:
    same_brand = similarity("TUF B850 WIFI", "ASUS", "TUF B850 WIFI", "ASUS")
    diff_brand = similarity("TUF B850 WIFI", "ASUS", "TUF B850 WIFI", "MSI")
    assert diff_brand < same_brand


def test_partial_overlap__between_zero_and_one() -> None:
    score = similarity("ASUS TUF B850 WIFI", "ASUS", "ASUS TUF B650 WIFI", "ASUS")
    assert 0.0 < score < 1.0


def test_empty__zero() -> None:
    assert similarity("", None, "anything", None) == 0.0

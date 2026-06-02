"""Vehicle import eligibility — US 25-year and Canada 15-year rules."""

from __future__ import annotations

from datetime import date

US_IMPORT_MIN_AGE = 25
CA_IMPORT_MIN_AGE = 15


def import_max_year_us(*, reference_year: int | None = None) -> int:
    """Latest model year eligible for US classic import (25+ years old)."""
    return (reference_year or date.today().year) - US_IMPORT_MIN_AGE


def import_max_year_ca(*, reference_year: int | None = None) -> int:
    """Latest model year eligible for Canadian import (15+ years old)."""
    return (reference_year or date.today().year) - CA_IMPORT_MIN_AGE


def us_import_eligible(year: int | None, *, reference_year: int | None = None) -> bool:
    if year is None:
        return False
    return year <= import_max_year_us(reference_year=reference_year)


def ca_import_eligible(year: int | None, *, reference_year: int | None = None) -> bool:
    if year is None:
        return False
    return year <= import_max_year_ca(reference_year=reference_year)


def import_badges(year: int | None, *, reference_year: int | None = None) -> list[str]:
    badges: list[str] = []
    if us_import_eligible(year, reference_year=reference_year):
        badges.append("US import (25+ yr)")
    if ca_import_eligible(year, reference_year=reference_year):
        badges.append("CA import (15+ yr)")
    return badges


def import_year_cap(
    *,
    import_us: bool,
    import_ca: bool,
    reference_year: int | None = None,
) -> int | None:
    """SQL/Meilisearch year ceiling when one or both import toggles are active."""
    limits: list[int] = []
    if import_us:
        limits.append(import_max_year_us(reference_year=reference_year))
    if import_ca:
        limits.append(import_max_year_ca(reference_year=reference_year))
    if not limits:
        return None
    return max(limits)

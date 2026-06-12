"""Tests for US/CA import eligibility rules."""

from notification_rake.analysis.import_rules import (
    ca_import_eligible,
    import_badges,
    import_max_year_ca,
    import_max_year_us,
    import_year_cap,
    us_import_eligible,
)


def test_us_25_year_rule():
    ref = 2026
    assert import_max_year_us(reference_year=ref) == 2001
    assert us_import_eligible(2001, reference_year=ref)
    assert us_import_eligible(1990, reference_year=ref)
    assert not us_import_eligible(2002, reference_year=ref)
    assert not us_import_eligible(None, reference_year=ref)


def test_ca_15_year_rule():
    ref = 2026
    assert import_max_year_ca(reference_year=ref) == 2011
    assert ca_import_eligible(2011, reference_year=ref)
    assert ca_import_eligible(2000, reference_year=ref)
    assert not ca_import_eligible(2012, reference_year=ref)


def test_import_badges():
    ref = 2026
    assert import_badges(1990, reference_year=ref) == [
        "US import (25+ yr)",
        "CA import (15+ yr)",
    ]
    assert import_badges(2010, reference_year=ref) == ["CA import (15+ yr)"]
    assert import_badges(2018, reference_year=ref) == []


def test_import_year_cap():
    ref = 2026
    assert import_year_cap(import_us=True, import_ca=False, reference_year=ref) == 2001
    assert import_year_cap(import_us=False, import_ca=True, reference_year=ref) == 2011
    assert import_year_cap(import_us=True, import_ca=True, reference_year=ref) == 2011
    assert import_year_cap(import_us=False, import_ca=False, reference_year=ref) is None

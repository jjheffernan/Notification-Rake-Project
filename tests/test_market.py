"""Tests for make/model market analytics."""

from notification_rake.search.market import slug_to_label, slugify


def test_slugify():
    assert slugify("Nissan Stagea") == "nissan-stagea"
    assert slugify("BMW M3") == "bmw-m3"


def test_slug_to_label():
    assert slug_to_label("nissan-stagea") == "Nissan Stagea"
    assert slug_to_label("bmw-m3") == "Bmw M3"

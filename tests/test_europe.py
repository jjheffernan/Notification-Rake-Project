"""Tests for UK/DE marketplace ingestion."""

from notification_rake.ingestion.europe.normalize import (
    fetch_europe_listings,
    fetch_source_listings,
)
from notification_rake.models.regions import SOURCE_COUNTRY, country_for_source


def test_europe_fixture_sources():
    items = fetch_europe_listings(limit=50)
    sources = {item.source for item in items}
    assert "ebay_uk" in sources
    assert "mobile_de" in sources
    assert "gumtree" in sources
    assert "copart_de" in sources
    assert len(items) >= 8


def test_europe_listings_have_country():
    items = fetch_europe_listings(limit=50)
    for item in items:
        assert item.country in {"GB", "DE"}
        assert item.price is not None
        assert item.image_urls


def test_fetch_single_eu_source():
    items = fetch_source_listings("autoscout24_uk", limit=10)
    assert len(items) >= 1
    assert all(i.source == "autoscout24_uk" for i in items)


def test_eu_source_country_registry():
    assert country_for_source("ebay_uk") == "GB"
    assert country_for_source("mobile_de") == "DE"
    assert SOURCE_COUNTRY["copart_uk"] == "GB"

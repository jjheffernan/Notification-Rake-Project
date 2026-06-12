"""Tests for Cars & Bids ingestion."""

from notification_rake.ingestion.carsandbids.normalize import fetch_listings
from notification_rake.models.regions import country_for_source


def test_carsandbids_fixture_fetch():
    items = fetch_listings(mode="", limit=10)
    assert len(items) >= 3
    sources = {item.source for item in items}
    assert sources == {"carsandbids"}


def test_carsandbids_stagea_sample():
    items = fetch_listings(query="Stagea", limit=10)
    assert len(items) >= 1
    stagea = items[0]
    assert "Stagea" in (stagea.title or "")
    assert stagea.make == "Nissan"
    assert stagea.model == "Stagea"
    assert stagea.year == 1998
    assert stagea.metadata.get("platform") == "carsandbids"


def test_carsandbids_country():
    assert country_for_source("carsandbids") == "US"

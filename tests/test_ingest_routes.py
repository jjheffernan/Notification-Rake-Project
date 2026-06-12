"""Tests for ingest route registry."""

from notification_rake.models.ingest_routes import (
    bulk_ingest_route_slugs,
    get_route,
    route_for_source,
    sources_for_route,
)


def test_us_auction_route_sources():
    sources = sources_for_route("us-auction")
    assert sources is not None
    assert "copart" in sources
    assert "carsandbids" in sources


def test_route_for_source():
    assert route_for_source("copart") == "us-auction"
    assert route_for_source("yahoo_auctions_jp") == "jp"
    assert route_for_source("mobile_de") == "de"
    assert route_for_source("craigslist") == "us-retail"


def test_bulk_routes_exclude_connected():
    slugs = bulk_ingest_route_slugs()
    assert "connected" not in slugs
    assert "us-retail" in slugs
    assert "jp" in slugs


def test_get_route_unknown():
    assert get_route("not-a-route") is None

from unittest.mock import patch

import httpx

from notification_rake.models import VehicleListing
from notification_rake.transform.geocode import (
    geocode_listings,
    geocode_nominatim,
    region_from_search_url,
    resolve_coords,
)


def test_region_from_search_url():
    assert region_from_search_url("https://sfbay.craigslist.org/search/cta?format=rss") == "sfbay"
    assert region_from_search_url("https://example.com") is None


def test_resolve_coords_uses_listing_fields():
    listing = VehicleListing(
        source="c",
        source_listing_id="1",
        longitude=-118.0,
        latitude=34.0,
    )
    lon, lat = resolve_coords(listing)
    assert lon == -118.0
    assert lat == 34.0


def test_resolve_coords_uses_region_centroid():
    listing = VehicleListing(source="c", source_listing_id="1")
    lon, lat = resolve_coords(
        listing,
        search_url="https://sfbay.craigslist.org/search/cta?format=rss",
    )
    assert lon == -122.4194
    assert lat == 37.7749


def test_geocode_listings_sets_missing_coords():
    items = [VehicleListing(source="c", source_listing_id="1")]
    out = geocode_listings(
        items,
        search_url="https://sfbay.craigslist.org/search/cta?format=rss",
    )
    assert out[0].longitude == -122.4194
    assert out[0].latitude == 37.7749


def test_geocode_nominatim_parses_response():
    payload = [{"lon": "-87.6298", "lat": "41.8781"}]
    ok = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("GET", "https://nominatim.openstreetmap.org/search"),
    )
    with patch.object(httpx.Client, "get", return_value=ok):
        coords = geocode_nominatim("chicago, United States")
    assert coords == (-87.6298, 41.8781)

"""ISO country codes and source → region mapping."""

from __future__ import annotations

SOURCE_COUNTRY: dict[str, str] = {
    "craigslist": "US",
    "yahoo_auctions_jp": "JP",
    "copart": "US",
    "ebay": "US",
    "ebay_uk": "GB",
    "gumtree": "GB",
    "autoscout24_uk": "GB",
    "copart_uk": "GB",
    "mobile_de": "DE",
    "autoscout24_de": "DE",
    "ebay_de": "DE",
    "copart_de": "DE",
    "carsandbids": "US",
}

REGION_LABELS: dict[str, str] = {
    "US": "United States",
    "CA": "Canada",
    "JP": "Japan",
    "GB": "United Kingdom",
    "DE": "Germany",
}

REGION_CENTERS: dict[str, tuple[float, float]] = {
    "US": (-122.4194, 37.7749),
    "CA": (-79.3832, 43.6532),
    "JP": (139.6503, 35.6762),
    "GB": (-0.1278, 51.5074),
    "DE": (13.405, 52.52),
}


def country_for_source(source: str) -> str | None:
    return SOURCE_COUNTRY.get(source)

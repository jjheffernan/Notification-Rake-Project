"""Resolve listing coordinates — Nominatim with region/search URL fallbacks."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from notification_rake.config import settings
from notification_rake.models.listing import VehicleListing
from notification_rake.models.regions import REGION_CENTERS

# Common Craigslist region subdomains → (lon, lat)
REGION_CENTROIDS: dict[str, tuple[float, float]] = {
    "sfbay": (-122.4194, 37.7749),
    "losangeles": (-118.2437, 34.0522),
    "newyork": (-74.0060, 40.7128),
    "seattle": (-122.3321, 47.6062),
    "portland": (-122.6765, 45.5152),
    "chicago": (-87.6298, 41.8781),
    "atlanta": (-84.3880, 33.7490),
    "boston": (-71.0589, 42.3601),
}


def region_from_search_url(search_url: str) -> str | None:
    """Extract Craigslist region slug from RSS/search URL host."""
    host = urlparse(search_url).netloc.lower()
    if not host.endswith(".craigslist.org"):
        return None
    return host.removesuffix(".craigslist.org") or None


def geocode_nominatim(query: str, *, user_agent: str | None = None) -> tuple[float, float] | None:
    """Forward geocode via Nominatim; returns (lon, lat) or None."""
    ua = user_agent or settings.geocode_user_agent
    url = f"{settings.nominatim_url.rstrip('/')}/search"
    headers = {"User-Agent": ua, "Accept": "application/json"}
    with httpx.Client(timeout=15.0, headers=headers) as client:
        resp = client.get(url, params={"q": query, "format": "json", "limit": 1})
        resp.raise_for_status()
        rows = resp.json()
    if not rows:
        return None
    return float(rows[0]["lon"]), float(rows[0]["lat"])


def resolve_coords(
    listing: VehicleListing,
    *,
    search_url: str | None = None,
    default_lon: float | None = None,
    default_lat: float | None = None,
) -> tuple[float, float]:
    """Best-effort coordinates: listing fields → region centroid → Nominatim → defaults."""
    if listing.longitude is not None and listing.latitude is not None:
        return listing.longitude, listing.latitude

    if listing.country and listing.country in REGION_CENTERS:
        return REGION_CENTERS[listing.country]

    region = region_from_search_url(search_url or settings.craigslist_search_rss)
    if region:
        if region in REGION_CENTROIDS:
            return REGION_CENTROIDS[region]
        label = region.replace("-", " ")
        try:
            coords = geocode_nominatim(f"{label}, United States")
            if coords:
                return coords
        except httpx.HTTPError:
            pass

    return (
        default_lon if default_lon is not None else settings.default_lon,
        default_lat if default_lat is not None else settings.default_lat,
    )


def geocode_listings(
    listings: list[VehicleListing],
    *,
    search_url: str | None = None,
    default_lon: float | None = None,
    default_lat: float | None = None,
) -> list[VehicleListing]:
    """Attach longitude/latitude to each listing when missing."""
    out: list[VehicleListing] = []
    for item in listings:
        lon, lat = resolve_coords(
            item,
            search_url=search_url,
            default_lon=default_lon,
            default_lat=default_lat,
        )
        out.append(item.model_copy(update={"longitude": lon, "latitude": lat}))
    return out

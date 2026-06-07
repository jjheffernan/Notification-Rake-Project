"""Ingest route registry — isolated pipelines per market/source group."""

from __future__ import annotations

from dataclasses import dataclass

from notification_rake.models.regions import SOURCE_COUNTRY


@dataclass(frozen=True)
class IngestRoute:
    """One ingest/search route: fetch, sync, and filter as a unit."""

    slug: str
    label: str
    sources: frozenset[str]
    country: str | None = None
    description: str = ""


INGEST_ROUTES: dict[str, IngestRoute] = {
    "us-retail": IngestRoute(
        slug="us-retail",
        label="US retail",
        sources=frozenset({"craigslist", "ebay"}),
        country="US",
        description="Craigslist RSS and eBay US classified listings",
    ),
    "us-auction": IngestRoute(
        slug="us-auction",
        label="US auctions",
        sources=frozenset({"copart", "carsandbids"}),
        country="US",
        description="Copart salvage and Cars & Bids enthusiast auctions",
    ),
    "jp": IngestRoute(
        slug="jp",
        label="Japan",
        sources=frozenset({"yahoo_auctions_jp"}),
        country="JP",
        description="Yahoo Auctions Japan vehicle listings",
    ),
    "uk": IngestRoute(
        slug="uk",
        label="United Kingdom",
        sources=frozenset({"ebay_uk", "gumtree", "autoscout24_uk", "copart_uk"}),
        country="GB",
        description="eBay UK, Gumtree, AutoScout24, Copart UK",
    ),
    "de": IngestRoute(
        slug="de",
        label="Germany",
        sources=frozenset({"mobile_de", "autoscout24_de", "ebay_de", "copart_de"}),
        country="DE",
        description="mobile.de, AutoScout24, eBay DE, Copart DE",
    ),
    "connected": IngestRoute(
        slug="connected",
        label="Connected accounts",
        sources=frozenset(),
        country=None,
        description="User-linked marketplace accounts (profile-scoped sync)",
    ),
}

_SINGLE_SOURCE_SLUGS = (
    "craigslist",
    "copart",
    "carsandbids",
    "yahoo_auctions_jp",
    "ebay_uk",
    "gumtree",
    "mobile_de",
)
for _source in _SINGLE_SOURCE_SLUGS:
    INGEST_ROUTES[_source] = IngestRoute(
        slug=_source,
        label=_source.replace("_", " ").title(),
        sources=frozenset({_source}),
        country=SOURCE_COUNTRY.get(_source),
    )


def get_route(slug: str) -> IngestRoute | None:
    return INGEST_ROUTES.get(slug.strip().lower())


def list_routes(*, include_connected: bool = True) -> list[IngestRoute]:
    seen: set[str] = set()
    routes: list[IngestRoute] = []
    for route in INGEST_ROUTES.values():
        if route.slug in seen:
            continue
        seen.add(route.slug)
        if route.slug == "connected" and not include_connected:
            continue
        routes.append(route)
    return sorted(routes, key=lambda r: r.label)


def sources_for_route(slug: str) -> frozenset[str] | None:
    route = get_route(slug)
    if not route:
        return None
    return route.sources if route.sources else None


def route_for_source(source: str) -> str | None:
    """Primary grouped route for a source slug (prefers market routes over single-source)."""
    source = source.strip().lower()
    for slug in ("us-retail", "us-auction", "jp", "uk", "de"):
        route = INGEST_ROUTES[slug]
        if source in route.sources:
            return slug
    if source in INGEST_ROUTES:
        return source
    return None


def bulk_ingest_route_slugs() -> list[str]:
    """Routes run by ingest_all (excludes connected — requires profile)."""
    return ["us-retail", "us-auction", "jp", "uk", "de"]

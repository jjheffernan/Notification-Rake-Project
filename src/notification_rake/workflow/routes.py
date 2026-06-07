"""Isolated per-route ingest pipelines — fetch, sync, and job tracking per route."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from notification_rake.config import settings
from notification_rake.ingestion.carsandbids.normalize import fetch_listings as fetch_carsandbids
from notification_rake.ingestion.connectors import fetch_all_connected
from notification_rake.ingestion.copart.normalize import fetch_listings as fetch_copart
from notification_rake.ingestion.craigslist import fetch_listings as fetch_craigslist
from notification_rake.ingestion.europe import fetch_europe_listings
from notification_rake.ingestion.raw import get_raw_listing_id, store_raw_listings
from notification_rake.ingestion.yahoo.normalize import fetch_yahoo_listings
from notification_rake.models.ingest_routes import (
    bulk_ingest_route_slugs,
    get_route,
    list_routes,
    sources_for_route,
)
from notification_rake.models.listing import VehicleListing
from notification_rake.models.regions import REGION_CENTERS
from notification_rake.notifications.alerts import notify_new_listings
from notification_rake.storage.accounts import enabled_connector_configs, list_accounts, mark_sync
from notification_rake.storage.auction import sync_auction_lot
from notification_rake.storage.db import seed_catalog, upsert_listings
from notification_rake.storage.metadata import finish_job, start_job
from notification_rake.transform.geocode import geocode_listings
from notification_rake.transform.normalize import load_catalog, normalize_listings
from notification_rake.workflow.pipeline import PipelineResult, _sync_search_index

logger = logging.getLogger(__name__)


@dataclass
class RouteRunResult:
    route: str
    result: PipelineResult
    sources: list[str] = field(default_factory=list)


def _geocode_defaults(route_slug: str) -> tuple[float | None, float | None, str | None]:
    route = get_route(route_slug)
    search_url = settings.craigslist_search_rss
    if route_slug == "us-retail" or route_slug == "craigslist":
        return settings.default_lon, settings.default_lat, search_url
    if route and route.country and route.country in REGION_CENTERS:
        lon, lat = REGION_CENTERS[route.country]
        return lon, lat, None
    return settings.default_lon, settings.default_lat, search_url


def fetch_route(route_slug: str, *, profile_id: str | None = None) -> list[VehicleListing]:
    """Fetch listings for one ingest route only."""
    slug = route_slug.strip().lower()
    route = get_route(slug)
    if not route:
        raise ValueError(f"unknown ingest route: {route_slug}")

    if slug == "us-retail" or slug == "craigslist":
        return fetch_craigslist(settings.craigslist_search_rss)

    if slug == "us-auction":
        items: list[VehicleListing] = []
        if settings.copart_enabled:
            items.extend(fetch_copart(limit=settings.copart_ingest_limit))
        if settings.carsandbids_enabled:
            items.extend(fetch_carsandbids(limit=settings.carsandbids_ingest_limit))
        return items

    if slug == "copart":
        return fetch_copart(limit=settings.copart_ingest_limit)

    if slug == "carsandbids":
        return fetch_carsandbids(limit=settings.carsandbids_ingest_limit)

    if slug == "jp" or slug == "yahoo_auctions_jp":
        return fetch_yahoo_listings(max_pages=1)

    if slug == "uk":
        if not settings.eu_marketplaces_enabled:
            return []
        return fetch_europe_listings(
            sources=sorted(sources_for_route("uk") or ()),
            limit=settings.eu_ingest_limit,
        )

    if slug == "de":
        if not settings.eu_marketplaces_enabled:
            return []
        return fetch_europe_listings(
            sources=sorted(sources_for_route("de") or ()),
            limit=settings.eu_ingest_limit,
        )

    if slug in {"ebay_uk", "gumtree", "mobile_de"}:
        if not settings.eu_marketplaces_enabled:
            return []
        return fetch_europe_listings(sources=[slug], limit=settings.eu_ingest_limit)

    if slug == "connected":
        if not profile_id:
            return []
        configs = enabled_connector_configs(settings.database_url, profile_id)
        return fetch_all_connected(configs)

    raise ValueError(f"fetch not implemented for route: {slug}")


def sync_route_listings(
    items: list[VehicleListing],
    route_slug: str,
    dsn: str | None = None,
    *,
    notify: bool = True,
) -> list[str]:
    """Normalize, geocode, upsert, and index listings for one route."""
    dsn = dsn or settings.database_url
    if not items:
        return []
    default_lon, default_lat, search_url = _geocode_defaults(route_slug)
    seed_catalog(dsn)
    store_raw_listings(dsn, items)
    catalog = load_catalog(dsn)
    normalized = normalize_listings(items, catalog)
    geocoded = geocode_listings(
        normalized,
        search_url=search_url,
        default_lon=default_lon,
        default_lat=default_lat,
    )
    results = upsert_listings(geocoded, catalog, dsn)
    for result in results:
        raw_id = get_raw_listing_id(
            dsn, result.listing.source, result.listing.source_listing_id
        )
        if raw_id:
            sync_auction_lot(dsn, raw_id, result.listing)
    if notify:
        notify_new_listings([r.listing for r in results if r.is_new])
    _sync_search_index(dsn, [r.id for r in results])
    return [r.id for r in results]


def run_route(
    route_slug: str,
    dsn: str | None = None,
    *,
    profile_id: str | None = None,
    notify: bool = True,
    track_job: bool = True,
) -> RouteRunResult:
    """Run an isolated ingest pipeline for a single route."""
    dsn = dsn or settings.database_url
    slug = route_slug.strip().lower()
    route = get_route(slug)
    if not route:
        raise ValueError(f"unknown ingest route: {route_slug}")

    job_name = f"route:{slug}"
    job_id = start_job(dsn, job_name) if track_job else None
    try:
        items = fetch_route(slug, profile_id=profile_id)
        source_set = sorted({item.source for item in items})
        seed_catalog(dsn)
        raw_stored, _ = store_raw_listings(dsn, items)
        catalog = load_catalog(dsn)
        normalized = normalize_listings(items, catalog)
        matched = sum(1 for n in normalized if n.make and n.model)
        default_lon, default_lat, search_url = _geocode_defaults(slug)
        geocoded = geocode_listings(
            normalized,
            search_url=search_url,
            default_lon=default_lon,
            default_lat=default_lat,
        )
        results = upsert_listings(geocoded, catalog, dsn)
        for result in results:
            raw_id = get_raw_listing_id(
                dsn, result.listing.source, result.listing.source_listing_id
            )
            if raw_id:
                sync_auction_lot(dsn, raw_id, result.listing)
        new_listings = [r.listing for r in results if r.is_new]
        alerted = notify_new_listings(new_listings) if notify else 0
        _sync_search_index(dsn, [r.id for r in results])

        if slug == "connected" and profile_id:
            accounts = [a for a in list_accounts(dsn, profile_id) if a.enabled]
            for account in accounts:
                mark_sync(dsn, account.id, status="ok", count=len(results))

        pipeline_result = PipelineResult(
            fetched=len(items),
            normalized=len(normalized),
            matched=matched,
            upserted=len(results),
            new=len(new_listings),
            alerted=alerted,
            in_radius=len(results),
            raw_stored=raw_stored,
        )
        if job_id:
            finish_job(
                dsn,
                job_id,
                status="success",
                fetched=pipeline_result.fetched,
                matched=pipeline_result.matched,
                upserted=pipeline_result.upserted,
                new_listings=pipeline_result.new,
                alerted=pipeline_result.alerted,
            )
        return RouteRunResult(route=slug, result=pipeline_result, sources=source_set)
    except Exception as exc:
        if job_id:
            finish_job(dsn, job_id, status="failed", error_message=str(exc))
        raise


def run_all_routes(
    dsn: str | None = None,
    *,
    routes: list[str] | None = None,
    profile_id: str | None = None,
    notify: bool = True,
    track_job: bool = True,
    continue_on_error: bool = True,
) -> dict[str, RouteRunResult]:
    """Run each ingest route in isolation — failures do not block other routes."""
    dsn = dsn or settings.database_url
    slugs = routes or bulk_ingest_route_slugs()
    if profile_id and "connected" not in slugs:
        slugs = [*slugs, "connected"]

    outcomes: dict[str, RouteRunResult] = {}
    for slug in slugs:
        try:
            outcomes[slug] = run_route(
                slug,
                dsn=dsn,
                profile_id=profile_id,
                notify=notify,
                track_job=track_job,
            )
        except Exception as exc:
            logger.exception("route %s ingest failed", slug)
            if not continue_on_error:
                raise
            outcomes[slug] = RouteRunResult(
                route=slug,
                result=PipelineResult(
                    fetched=0,
                    normalized=0,
                    matched=0,
                    upserted=0,
                    new=0,
                    alerted=0,
                    in_radius=0,
                    raw_stored=0,
                ),
                sources=[],
            )
            logger.warning("route %s skipped after error: %s", slug, exc)
    return outcomes


def merge_route_results(results: dict[str, RouteRunResult]) -> PipelineResult:
    """Aggregate isolated route runs into one PipelineResult."""
    total = PipelineResult(
        fetched=0,
        normalized=0,
        matched=0,
        upserted=0,
        new=0,
        alerted=0,
        in_radius=0,
        raw_stored=0,
    )
    for run in results.values():
        r = run.result
        total.fetched += r.fetched
        total.normalized += r.normalized
        total.matched += r.matched
        total.upserted += r.upserted
        total.new += r.new
        total.alerted += r.alerted
        total.in_radius += r.in_radius
        total.raw_stored += r.raw_stored
    return total


def route_catalog() -> list[dict[str, object]]:
    """Serializable route metadata for API/UI."""
    return [
        {
            "slug": route.slug,
            "label": route.label,
            "country": route.country,
            "sources": sorted(route.sources),
            "description": route.description,
        }
        for route in list_routes(include_connected=True)
    ]

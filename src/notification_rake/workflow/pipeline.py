"""Ingest → normalize → geocode → upsert → alert orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from notification_rake.config import settings
from notification_rake.ingestion.craigslist import fetch_listings
from notification_rake.ingestion.raw import store_raw_listings
from notification_rake.models.listing import VehicleListing
from notification_rake.notifications.alerts import notify_new_listings
from notification_rake.storage.db import search_within_radius, seed_catalog, upsert_listings
from notification_rake.storage.metadata import finish_job, start_job
from notification_rake.transform.geocode import geocode_listings
from notification_rake.transform.normalize import load_catalog, normalize_listings


def _sync_search_index(dsn: str, listing_ids: list[str]) -> None:
    try:
        from notification_rake.search.meilisearch_client import sync_documents

        sync_documents(dsn, listing_ids or None)
    except Exception:
        pass


@dataclass
class PipelineResult:
    fetched: int
    normalized: int
    matched: int
    upserted: int
    new: int
    alerted: int
    in_radius: int
    raw_stored: int = 0


def ingest(search_url: str | None = None) -> list[VehicleListing]:
    return fetch_listings(search_url or settings.craigslist_search_rss)


def normalize(items: list[VehicleListing], dsn: str | None = None) -> list[VehicleListing]:
    catalog = load_catalog(dsn or settings.database_url)
    return normalize_listings(items, catalog)


def sync(
    items: list[VehicleListing],
    dsn: str | None = None,
    *,
    search_url: str | None = None,
    lon: float | None = None,
    lat: float | None = None,
    notify: bool = True,
) -> list[str]:
    dsn = dsn or settings.database_url
    url = search_url or settings.craigslist_search_rss
    seed_catalog(dsn)
    store_raw_listings(dsn, items)
    catalog = load_catalog(dsn)
    normalized = normalize_listings(items, catalog)
    geocoded = geocode_listings(
        normalized,
        search_url=url,
        default_lon=lon,
        default_lat=lat,
    )
    results = upsert_listings(geocoded, catalog, dsn)
    if notify:
        notify_new_listings([r.listing for r in results if r.is_new])
    _sync_search_index(dsn, [r.id for r in results])
    return [r.id for r in results]


def run_pipeline(
    search_url: str | None = None,
    dsn: str | None = None,
    *,
    lon: float | None = None,
    lat: float | None = None,
    radius_m: float = 50_000,
    notify: bool = True,
    track_job: bool = True,
) -> PipelineResult:
    dsn = dsn or settings.database_url
    url = search_url or settings.craigslist_search_rss
    seed_catalog(dsn)
    job_id = start_job(dsn, "pipeline") if track_job else None
    try:
        raw = ingest(url)
        raw_stored, _ = store_raw_listings(dsn, raw)
        catalog = load_catalog(dsn)
        normalized = normalize_listings(raw, catalog)
        matched = sum(1 for n in normalized if n.make and n.model)
        geocoded = geocode_listings(
            normalized,
            search_url=url,
            default_lon=lon,
            default_lat=lat,
        )
        results = upsert_listings(geocoded, catalog, dsn)
        new_listings = [r.listing for r in results if r.is_new]
        alerted = notify_new_listings(new_listings) if notify else 0
        _sync_search_index(dsn, [r.id for r in results])
        origin_lon = lon if lon is not None else settings.default_lon
        origin_lat = lat if lat is not None else settings.default_lat
        nearby = search_within_radius(
            dsn,
            lon=origin_lon,
            lat=origin_lat,
            radius_m=radius_m,
        )
        result = PipelineResult(
            fetched=len(raw),
            normalized=len(normalized),
            matched=matched,
            upserted=len(results),
            new=len(new_listings),
            alerted=alerted,
            in_radius=len(nearby),
            raw_stored=raw_stored,
        )
        if job_id:
            finish_job(
                dsn,
                job_id,
                status="success",
                fetched=result.fetched,
                matched=result.matched,
                upserted=result.upserted,
                new_listings=result.new,
                alerted=result.alerted,
            )
        return result
    except Exception as exc:
        if job_id:
            finish_job(dsn, job_id, status="failed", error_message=str(exc))
        raise

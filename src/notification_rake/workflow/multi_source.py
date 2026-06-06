"""Multi-source ingest orchestration — delegates to isolated route pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field

from notification_rake.config import settings
from notification_rake.ingestion.carsandbids.normalize import fetch_listings as fetch_carsandbids
from notification_rake.ingestion.copart.normalize import fetch_listings as fetch_copart
from notification_rake.ingestion.europe import fetch_europe_listings
from notification_rake.ingestion.yahoo.normalize import fetch_yahoo_listings
from notification_rake.models.listing import VehicleListing
from notification_rake.storage.accounts import list_accounts
from notification_rake.workflow.pipeline import PipelineResult
from notification_rake.workflow.routes import (
    fetch_route,
    merge_route_results,
    run_all_routes,
    run_route,
)
from notification_rake.workflow.routes import (
    sync_route_listings as _sync_route_listings,
)


def sync_listings(
    items: list[VehicleListing],
    dsn: str | None = None,
    *,
    notify: bool = True,
    route_slug: str | None = None,
) -> list[str]:
    """Sync listings using route-aware geocode defaults."""
    from notification_rake.models.ingest_routes import route_for_source

    slug = route_slug
    if not slug and items:
        slug = route_for_source(items[0].source)
    if not slug:
        slug = "us-retail"
    return _sync_route_listings(items, slug, dsn=dsn, notify=notify)


@dataclass
class MultiSourceResult:
    by_source: dict[str, int] = field(default_factory=dict)
    by_route: dict[str, int] = field(default_factory=dict)
    upserted: int = 0
    new: int = 0
    alerted: int = 0
    connected: int = 0


def fetch_all_sources(*, profile_id: str | None = None) -> list[VehicleListing]:
    """Legacy bulk fetch — prefer fetch_route() per pipeline."""
    from notification_rake.models.ingest_routes import bulk_ingest_route_slugs

    items: list[VehicleListing] = []
    for slug in bulk_ingest_route_slugs():
        items.extend(fetch_route(slug, profile_id=profile_id))
    if profile_id:
        items.extend(fetch_route("connected", profile_id=profile_id))
    return items


def ingest_copart(
    *, query: str = "", state: str | None = None, limit: int = 50
) -> list[VehicleListing]:
    return fetch_copart(query=query, state=state, limit=limit)


def ingest_yahoo(*, query: str = "", max_pages: int = 1) -> list[VehicleListing]:
    return fetch_yahoo_listings(query=query, max_pages=max_pages)


def ingest_europe(*, query: str = "", limit: int = 50) -> list[VehicleListing]:
    return fetch_europe_listings(query=query, limit=limit)


def ingest_carsandbids(
    *, query: str = "", mode: str = "active", limit: int = 50
) -> list[VehicleListing]:
    return fetch_carsandbids(query=query, mode=mode, limit=limit)


def run_connected_sync(profile_id: str, dsn: str | None = None) -> MultiSourceResult:
    dsn = dsn or settings.database_url
    run = run_route("connected", dsn=dsn, profile_id=profile_id, notify=False)
    accounts = [a for a in list_accounts(dsn, profile_id) if a.enabled]
    return MultiSourceResult(
        by_source={s: run.result.upserted for s in run.sources},
        by_route={"connected": run.result.upserted},
        upserted=run.result.upserted,
        new=run.result.new,
        connected=len(accounts),
    )


def run_all_sources(
    dsn: str | None = None,
    *,
    profile_id: str | None = None,
    notify: bool = True,
    track_job: bool = True,
) -> PipelineResult:
    """Run all bulk ingest routes in isolation and merge results."""
    outcomes = run_all_routes(
        dsn=dsn,
        profile_id=profile_id,
        notify=notify,
        track_job=track_job,
        continue_on_error=True,
    )
    return merge_route_results(outcomes)

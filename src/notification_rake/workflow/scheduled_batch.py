"""Scheduled batch — refresh ingest routes and run due vehicle watchlist searches."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from notification_rake.config import settings
from notification_rake.models.ingest_routes import bulk_ingest_route_slugs
from notification_rake.models.listing import VehicleListing
from notification_rake.notifications.alerts import notify_new_listings
from notification_rake.search.service import ListingSearch, search_listings
from notification_rake.storage.metadata import finish_job, start_job
from notification_rake.storage.scheduled_searches import (
    ScheduledSearch,
    get_scheduled_search,
    list_due_searches,
    list_scheduled_searches,
    record_search_run,
)
from notification_rake.workflow.routes import merge_route_results, run_all_routes, run_route

logger = logging.getLogger(__name__)


@dataclass
class SearchRunOutcome:
    search_id: str
    name: str
    match_count: int = 0
    new_count: int = 0
    alerted: int = 0
    error: str | None = None


@dataclass
class BatchRunResult:
    ingest_routes: list[str] = field(default_factory=list)
    ingest_upserted: int = 0
    searches_run: int = 0
    total_new_matches: int = 0
    total_alerted: int = 0
    outcomes: list[SearchRunOutcome] = field(default_factory=list)


def _search_from_query(query_json: dict) -> ListingSearch:
    return ListingSearch(
        q=query_json.get("q") or None,
        make=query_json.get("make") or None,
        model=query_json.get("model") or None,
        source=query_json.get("source") or None,
        route=query_json.get("route") or None,
        country=query_json.get("country") or None,
        import_us=bool(query_json.get("import_us")),
        import_ca=bool(query_json.get("import_ca")),
        year_min=query_json.get("year_min"),
        year_max=query_json.get("year_max"),
        price_min=query_json.get("price_min"),
        price_max=query_json.get("price_max"),
        limit=min(int(query_json.get("limit") or 100), 100),
        offset=0,
    )


def _refresh_routes(dsn: str, routes: list[str]) -> int:
    if not routes:
        if not settings.scheduled_search_refresh_all:
            return 0
        outcomes = run_all_routes(dsn=dsn, notify=False, track_job=False, continue_on_error=True)
        return merge_route_results(outcomes).upserted

    upserted = 0
    for slug in routes:
        try:
            run = run_route(slug, dsn=dsn, notify=False, track_job=False)
            upserted += run.result.upserted
        except Exception as exc:
            logger.warning("scheduled refresh route %s failed: %s", slug, exc)
    return upserted


def _collect_routes_to_refresh(searches: list[ScheduledSearch]) -> list[str]:
    routes: set[str] = set()
    for s in searches:
        routes.update(s.ingest_routes)
    if routes:
        return sorted(routes)
    if settings.scheduled_search_refresh_all:
        return bulk_ingest_route_slugs()
    return []


def run_single_scheduled_search(
    dsn: str,
    search: ScheduledSearch,
    *,
    listings_by_id: dict[str, dict] | None = None,
) -> SearchRunOutcome:
    outcome = SearchRunOutcome(search_id=search.id, name=search.name)
    try:
        listing_search = _search_from_query(search.query_json)
        items, total = search_listings(dsn, listing_search)
        ids = [str(item["id"]) for item in items]
        prev = set(search.last_seen_ids)
        new_ids = [i for i in ids if i not in prev]
        outcome.match_count = total
        outcome.new_count = len(new_ids) if prev else 0

        if search.alert_enabled and new_ids and prev:
            to_alert: list[VehicleListing] = []
            for lid in new_ids[:20]:
                row = (listings_by_id or {}).get(lid) or next(
                    (it for it in items if str(it["id"]) == lid), None
                )
                if row:
                    to_alert.append(
                        VehicleListing(
                            source=row.get("source") or "listing",
                            source_listing_id=row.get("source_listing_id") or lid,
                            title=row.get("title"),
                            price=row.get("price"),
                            year=row.get("year"),
                            make=row.get("make"),
                            model=row.get("model"),
                        )
                    )
            if to_alert:
                outcome.alerted = notify_new_listings(to_alert)

        record_search_run(
            dsn,
            search.id,
            match_count=total,
            new_count=outcome.new_count,
            seen_ids=ids,
            interval_minutes=search.interval_minutes,
        )
    except Exception as exc:
        outcome.error = str(exc)
        logger.exception("scheduled search %s failed", search.id)
    return outcome


def run_scheduled_batch(
    dsn: str | None = None,
    *,
    force: bool = False,
    search_id: str | None = None,
    profile_id: str | None = None,
    track_job: bool = True,
) -> BatchRunResult:
    """Run due watchlist searches; optionally refresh ingest routes first."""
    dsn = dsn or settings.database_url
    job_id = start_job(dsn, "scheduled_batch") if track_job else None
    result = BatchRunResult()

    try:
        if search_id:
            one = get_scheduled_search(dsn, search_id)
            if one and profile_id and one.profile_id != profile_id:
                searches = []
            else:
                searches = [one] if one else []
        elif force:
            searches = list_scheduled_searches(
                dsn, profile_id=profile_id, enabled_only=True
            )
        else:
            searches = list_due_searches(dsn, profile_id=profile_id)

        refresh = _collect_routes_to_refresh(searches)
        result.ingest_routes = refresh
        result.ingest_upserted = _refresh_routes(dsn, refresh) if refresh else 0

        for search in searches:
            outcome = run_single_scheduled_search(dsn, search)
            result.outcomes.append(outcome)
            result.searches_run += 1
            result.total_new_matches += outcome.new_count
            result.total_alerted += outcome.alerted

        if job_id:
            finish_job(
                dsn,
                job_id,
                status="success",
                fetched=result.ingest_upserted,
                upserted=result.ingest_upserted,
                new_listings=result.total_new_matches,
                alerted=result.total_alerted,
            )
        return result
    except Exception as exc:
        if job_id:
            finish_job(dsn, job_id, status="failed", error_message=str(exc))
        raise

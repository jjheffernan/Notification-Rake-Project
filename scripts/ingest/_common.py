"""Shared wrappers for ingest container scripts."""

from __future__ import annotations

from collections.abc import Callable

from notification_rake.models.listing import VehicleListing
from notification_rake.workflow.routes import merge_route_results, run_all_routes, run_route


def exit_ok(ok: bool) -> int:
    return 0 if ok else 1


def run_route_script(route_slug: str, *, label: str | None = None) -> int:
    """Run a configured ingest route and print a standard summary line."""
    name = label or f"ingest_{route_slug.replace('-', '_')}"
    result = run_route(route_slug)
    r = result.result
    msg = f"{name}: fetched={r.fetched} upserted={r.upserted} new={r.new}"
    if result.sources:
        msg += f" sources={','.join(result.sources)}"
    print(msg)
    return exit_ok(r.upserted > 0)


def run_all_routes_script(*, label: str = "ingest_all") -> int:
    """Run every bulk ingest route and merge results."""
    outcomes = run_all_routes(continue_on_error=True)
    result = merge_route_results(outcomes)
    parts = " ".join(f"{slug}={run.result.upserted}" for slug, run in outcomes.items())
    print(
        f"{label}: fetched={result.fetched} upserted={result.upserted} "
        f"new={result.new} [{parts}]"
    )
    return exit_ok(result.upserted > 0)


def run_source_script(
    fetch: Callable[..., list[VehicleListing]],
    *,
    label: str,
    **fetch_kwargs: object,
) -> int:
    """Fetch from a single source module and upsert listings."""
    from notification_rake.workflow.multi_source import sync_listings

    items = fetch(**fetch_kwargs)
    ids = sync_listings(items)
    print(f"{label}: fetched={len(items)} upserted={len(ids)}")
    return exit_ok(bool(ids))

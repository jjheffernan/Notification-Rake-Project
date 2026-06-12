"""Tests for isolated route ingest pipelines."""

from unittest.mock import patch

from notification_rake.models.listing import VehicleListing
from notification_rake.workflow.pipeline import PipelineResult
from notification_rake.workflow.routes import (
    RouteRunResult,
    fetch_route,
    merge_route_results,
    run_all_routes,
)


def _sample(source: str) -> VehicleListing:
    return VehicleListing(source=source, source_listing_id=f"{source}-1", title="Test")


def test_fetch_route_us_retail():
    sample = [_sample("craigslist")]
    with patch("notification_rake.workflow.routes.fetch_craigslist", return_value=sample):
        items = fetch_route("us-retail")
    assert len(items) == 1
    assert items[0].source == "craigslist"


def test_merge_route_results():
    merged = merge_route_results(
        {
            "jp": RouteRunResult(
                route="jp",
                result=PipelineResult(2, 2, 1, 2, 1, 0, 2, 2),
                sources=["yahoo_auctions_jp"],
            ),
            "uk": RouteRunResult(
                route="uk",
                result=PipelineResult(3, 3, 2, 3, 0, 0, 3, 3),
                sources=["ebay_uk"],
            ),
        }
    )
    assert merged.fetched == 5
    assert merged.upserted == 5


def test_run_all_routes_continues_on_error():
    ok = [_sample("yahoo_auctions_jp")]

    def fake_fetch(slug, **kwargs):
        if slug == "us-retail":
            raise RuntimeError("boom")
        if slug == "jp":
            return ok
        return []

    patches = [
        patch("notification_rake.workflow.routes.fetch_route", side_effect=fake_fetch),
        patch("notification_rake.workflow.routes._geocode_defaults", return_value=(0.0, 0.0, None)),
        patch("notification_rake.workflow.routes.seed_catalog"),
        patch("notification_rake.workflow.routes.store_raw_listings", return_value=(0, [])),
        patch("notification_rake.workflow.routes.load_catalog", return_value=[]),
        patch(
            "notification_rake.workflow.routes.normalize_listings",
            side_effect=lambda items, catalog: items,
        ),
        patch(
            "notification_rake.workflow.routes.geocode_listings",
            side_effect=lambda items, **kw: items,
        ),
        patch("notification_rake.workflow.routes.upsert_listings", return_value=[]),
        patch("notification_rake.workflow.routes.start_job", return_value=None),
    ]
    from contextlib import ExitStack

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        outcomes = run_all_routes(
            routes=["us-retail", "jp"],
            track_job=False,
            continue_on_error=True,
        )
    assert "us-retail" in outcomes
    assert "jp" in outcomes
    assert outcomes["jp"].result.fetched == 1

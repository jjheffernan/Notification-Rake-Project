"""Run US retail ingest route (Craigslist)."""

from __future__ import annotations

from notification_rake.workflow.routes import run_route


def run() -> int:
    result = run_route("us-retail")
    r = result.result
    print(f"ingest_us_retail: fetched={r.fetched} upserted={r.upserted} new={r.new}")
    return 0 if r.upserted > 0 else 1

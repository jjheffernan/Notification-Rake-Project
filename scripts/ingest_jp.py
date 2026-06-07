"""Run Japan ingest route (Yahoo Auctions JP)."""

from __future__ import annotations

from notification_rake.workflow.routes import run_route


def run() -> int:
    result = run_route("jp")
    r = result.result
    print(f"ingest_jp: fetched={r.fetched} upserted={r.upserted} new={r.new}")
    return 0 if r.upserted > 0 else 1

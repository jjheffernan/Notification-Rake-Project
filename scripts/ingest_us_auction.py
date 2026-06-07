"""Run US auction ingest route (Copart + Cars & Bids)."""

from __future__ import annotations

from notification_rake.workflow.routes import run_route


def run() -> int:
    result = run_route("us-auction")
    r = result.result
    print(
        f"ingest_us_auction: fetched={r.fetched} upserted={r.upserted} "
        f"sources={','.join(result.sources)}"
    )
    return 0 if r.upserted > 0 else 1

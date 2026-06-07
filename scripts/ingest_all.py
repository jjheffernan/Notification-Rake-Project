"""Full multi-route ingest — each pipeline runs in isolation."""

from __future__ import annotations

from notification_rake.workflow.routes import merge_route_results, run_all_routes


def run() -> int:
    outcomes = run_all_routes(continue_on_error=True)
    result = merge_route_results(outcomes)
    parts = " ".join(f"{slug}={run.result.upserted}" for slug, run in outcomes.items())
    print(
        f"ingest_all: fetched={result.fetched} upserted={result.upserted} "
        f"new={result.new} [{parts}]"
    )
    return 0 if result.upserted > 0 else 1

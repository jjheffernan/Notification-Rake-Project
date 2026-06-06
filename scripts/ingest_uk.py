"""Run UK ingest route."""

from __future__ import annotations

from notification_rake.workflow.routes import run_route


def run() -> int:
    result = run_route("uk")
    r = result.result
    print(f"ingest_uk: fetched={r.fetched} upserted={r.upserted} sources={','.join(result.sources)}")
    return 0 if r.upserted > 0 else 1

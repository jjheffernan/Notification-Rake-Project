"""Container script: full multi-source ingest."""

from __future__ import annotations

from notification_rake.workflow.multi_source import run_all_sources


def run() -> int:
    result = run_all_sources()
    print(
        f"pipeline: fetched={result.fetched} raw={result.raw_stored} "
        f"matched={result.matched} upserted={result.upserted} "
        f"new={result.new} alerted={result.alerted} in_radius={result.in_radius}"
    )
    return 0 if result.upserted > 0 else 1

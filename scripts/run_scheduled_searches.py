"""Run due watchlist searches (cron-friendly)."""

from __future__ import annotations

from notification_rake.workflow.scheduled_batch import run_scheduled_batch


def run() -> int:
    result = run_scheduled_batch(track_job=True)
    print(
        f"run_scheduled_searches: searches={result.searches_run} "
        f"new={result.total_new_matches} alerted={result.total_alerted} "
        f"ingest_upserted={result.ingest_upserted}"
    )
    return 0

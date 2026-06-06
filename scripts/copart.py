"""Copart auction ingest."""

from __future__ import annotations

from notification_rake.workflow.multi_source import ingest_copart, sync_listings


def run() -> int:
    items = ingest_copart()
    ids = sync_listings(items)
    print(f"copart: fetched={len(items)} upserted={len(ids)}")
    return 0 if ids else 1

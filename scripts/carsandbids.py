"""Cars & Bids auction ingest."""

from __future__ import annotations

from notification_rake.workflow.multi_source import ingest_carsandbids, sync_listings


def run() -> int:
    items = ingest_carsandbids()
    ids = sync_listings(items)
    print(f"carsandbids: fetched={len(items)} upserted={len(ids)}")
    return 0 if ids else 1

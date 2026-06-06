"""Yahoo Auctions JP ingest."""

from __future__ import annotations

from notification_rake.workflow.multi_source import ingest_yahoo, sync_listings


def run() -> int:
    items = ingest_yahoo()
    ids = sync_listings(items)
    print(f"yahoo: fetched={len(items)} upserted={len(ids)}")
    return 0 if ids else 1

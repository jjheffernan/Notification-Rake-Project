"""Container script: fetch Craigslist listings."""

from __future__ import annotations

from notification_rake.config import settings
from notification_rake.workflow import ingest


def run() -> int:
    listings = ingest()
    print(f"ingest: {len(listings)} listings from feed")
    for item in listings:
        print(f"  - {item.source_listing_id}: {item.title!r} (${item.price})")
    print(f"feed: {settings.craigslist_search_rss}")
    return 0

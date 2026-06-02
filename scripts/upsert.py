"""Container script: upsert listings to PostGIS."""

from __future__ import annotations

from notification_rake.config import settings
from notification_rake.workflow import ingest, normalize, sync


def run() -> int:
    raw = ingest()
    normalized = normalize(raw)
    ids = sync(normalized)
    print(f"upsert: {len(ids)} rows written to vehicle_listing")
    print(f"database: {settings.database_url}")
    return 0

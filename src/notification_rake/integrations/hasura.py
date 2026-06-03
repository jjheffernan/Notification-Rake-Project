"""Hasura metadata helpers — track Postgres tables for GraphQL."""

from __future__ import annotations

import httpx

from notification_rake.config import settings

# (schema, table) — search layer in public, raw + metadata in named schemas
TRACKED_TABLES: tuple[tuple[str, str], ...] = (
    ("public", "vehicle_make"),
    ("public", "vehicle_model"),
    ("public", "vehicle_listing"),
    ("listings", "source"),
    ("listings", "listing"),
    ("listings", "listing_history"),
    ("metadata", "job_runs"),
    ("metadata", "crawler_status"),
)


def track_tables(
    *,
    hasura_url: str | None = None,
    admin_secret: str | None = None,
) -> list[str]:
    """Track catalog, listings, and metadata tables in Hasura."""
    base = (hasura_url or settings.hasura_url).rstrip("/")
    secret = admin_secret or settings.hasura_admin_secret
    if not secret:
        raise ValueError("HASURA_ADMIN_SECRET is required to track tables")

    tracked: list[str] = []
    headers = {"x-hasura-admin-secret": secret, "Content-Type": "application/json"}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        for schema, table in TRACKED_TABLES:
            resp = client.post(
                f"{base}/v1/metadata",
                json={
                    "type": "pg_track_table",
                    "args": {
                        "source": "default",
                        "table": {"schema": schema, "name": table},
                    },
                },
            )
            label = f"{schema}.{table}"
            if resp.status_code == 400 and "already tracked" in resp.text.lower():
                tracked.append(label)
                continue
            resp.raise_for_status()
            tracked.append(label)
    return tracked

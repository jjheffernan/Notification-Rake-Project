"""Persist raw marketplace listings in the listings schema."""

from __future__ import annotations

import json
from typing import Any

from notification_rake.models.listing import VehicleListing

UPSERT_SOURCE = """
INSERT INTO listings.source (name, base_url)
VALUES (%(name)s, %(base_url)s)
ON CONFLICT (name) DO UPDATE SET base_url = COALESCE(EXCLUDED.base_url, listings.source.base_url)
RETURNING id;
"""

UPSERT_LISTING = """
INSERT INTO listings.listing (
    source_id, external_id, title, description, raw_payload,
    price, year, mileage, vin, url, scraped_at, updated_at
) VALUES (
    %(source_id)s, %(external_id)s, %(title)s, %(description)s, %(raw_payload)s,
    %(price)s, %(year)s, %(mileage)s, %(vin)s, %(url)s, now(), now()
)
ON CONFLICT (source_id, external_id) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    raw_payload = EXCLUDED.raw_payload,
    price = EXCLUDED.price,
    year = EXCLUDED.year,
    mileage = EXCLUDED.mileage,
    vin = EXCLUDED.vin,
    url = EXCLUDED.url,
    updated_at = now()
RETURNING id, (xmax = 0) AS is_new;
"""

INSERT_HISTORY = """
INSERT INTO listings.listing_history (listing_id, price, title)
VALUES (%(listing_id)s, %(price)s, %(title)s);
"""

UPSERT_IMAGE = """
INSERT INTO listings.listing_image (listing_id, url, position)
VALUES (%(listing_id)s, %(url)s, %(position)s)
ON CONFLICT (listing_id, url) DO NOTHING;
"""

GET_RAW_LISTING_ID = """
SELECT rl.id FROM listings.listing rl
JOIN listings.source src ON src.id = rl.source_id
WHERE src.name = %(source)s AND rl.external_id = %(external_id)s;
"""


def _payload(item: VehicleListing) -> dict[str, Any]:
    data = item.model_dump(mode="json")
    data.pop("scraped_at", None)
    return data


def _listing_url(item: VehicleListing) -> str | None:
    meta = item.metadata or {}
    for key in ("copart_url", "source_url", "item_web_url"):
        if meta.get(key):
            return str(meta[key])
    return None


def get_raw_listing_id(dsn: str, source: str, external_id: str) -> str | None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            GET_RAW_LISTING_ID,
            {"source": source, "external_id": external_id},
        ).fetchone()
    return str(row[0]) if row else None


def store_raw_listings(dsn: str, items: list[VehicleListing]) -> tuple[int, int]:
    """Upsert raw listings; returns (stored_count, new_count)."""
    import psycopg

    if not items:
        return 0, 0

    stored = 0
    new_count = 0
    from itertools import groupby

    sorted_items = sorted(items, key=lambda i: i.source)
    with psycopg.connect(dsn) as conn:
        for source_name, group in groupby(sorted_items, key=lambda i: i.source):
            batch = list(group)
            source_row = conn.execute(
                UPSERT_SOURCE,
                {"name": source_name, "base_url": None},
            ).fetchone()
            source_id = int(source_row[0])
            source_stored = 0

            for item in batch:
                row = conn.execute(
                    UPSERT_LISTING,
                    {
                        "source_id": source_id,
                        "external_id": item.source_listing_id,
                        "title": item.title,
                        "description": item.description,
                        "raw_payload": json.dumps(_payload(item)),
                        "price": item.price,
                        "year": item.year,
                        "mileage": item.mileage,
                        "vin": item.vin,
                        "url": _listing_url(item),
                    },
                ).fetchone()
                if not row:
                    continue
                listing_id = str(row[0])
                is_new = bool(row[1])
                stored += 1
                source_stored += 1
                if is_new:
                    new_count += 1
                conn.execute(
                    INSERT_HISTORY,
                    {"listing_id": listing_id, "price": item.price, "title": item.title},
                )
                for position, url in enumerate(item.image_urls):
                    conn.execute(
                        UPSERT_IMAGE,
                        {"listing_id": listing_id, "url": url, "position": position},
                    )

            conn.execute(
                """
                INSERT INTO metadata.crawler_status (
                    source_id, last_run_at, last_status, listings_seen
                )
                VALUES (%(source_id)s, now(), 'ok', %(count)s)
                ON CONFLICT (source_id) DO UPDATE SET
                    last_run_at = now(),
                    last_status = 'ok',
                    listings_seen = metadata.crawler_status.listings_seen + EXCLUDED.listings_seen,
                    updated_at = now();
                """,
                {"source_id": source_id, "count": source_stored},
            )

        conn.execute(
            """
            INSERT INTO metadata.sync_status (layer, records_synced, notes)
            VALUES ('listings', %(count)s, 'raw ingest');
            """,
            {"count": stored},
        )
        conn.commit()
    return stored, new_count

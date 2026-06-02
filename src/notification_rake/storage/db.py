"""Postgres upsert + geo queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from notification_rake.models.listing import VehicleListing
from notification_rake.models.regions import country_for_source
from notification_rake.transform.normalize import ModelRef, lookup_ids

SEED_CATALOG = """
INSERT INTO vehicle_make (name) VALUES
    ('Toyota'), ('Honda'), ('Ford'), ('Nissan')
ON CONFLICT DO NOTHING;

INSERT INTO vehicle_model (make_id, name)
SELECT mk.id, m.name
FROM vehicle_make mk
JOIN (VALUES
    ('Toyota', 'Camry'),
    ('Toyota', 'Corolla'),
    ('Toyota', 'RAV4'),
    ('Honda', 'Civic'),
    ('Honda', 'Accord'),
    ('Ford', 'F-150'),
    ('Nissan', 'Altima'),
    ('Nissan', 'Stagea')
) AS m(make_name, name) ON mk.name = m.make_name
ON CONFLICT DO NOTHING;
"""

GEO_FUNCTION = """
CREATE OR REPLACE FUNCTION public.listings_within_radius(
    origin_lon double precision,
    origin_lat double precision,
    radius_m double precision DEFAULT 50000
)
RETURNS TABLE (
    id uuid,
    title text,
    price numeric,
    year integer,
    make text,
    model text,
    meters double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT vl.id, vl.title, vl.price, vl.year,
           mk.name AS make, mo.name AS model,
           ST_Distance(
               vl.geom,
               ST_SetSRID(ST_MakePoint(origin_lon, origin_lat), 4326)::geography
           ) AS meters
    FROM vehicle_listing vl
    LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
    LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
    WHERE ST_DWithin(
        vl.geom,
        ST_SetSRID(ST_MakePoint(origin_lon, origin_lat), 4326)::geography,
        radius_m
    )
    ORDER BY meters;
$$;
"""

UPSERT_LISTING = """
INSERT INTO vehicle_listing (
    source, source_listing_id, title, make_id, model_id, year, price, country, geom
) VALUES (
    %(source)s, %(source_listing_id)s, %(title)s, %(make_id)s, %(model_id)s,
    %(year)s, %(price)s, %(country)s,
    ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
)
ON CONFLICT (source, source_listing_id) DO UPDATE SET
    title = EXCLUDED.title,
    make_id = EXCLUDED.make_id,
    model_id = EXCLUDED.model_id,
    year = EXCLUDED.year,
    price = EXCLUDED.price,
    country = EXCLUDED.country,
    geom = EXCLUDED.geom,
    updated_at = now()
RETURNING id, (xmax = 0) AS is_new;
"""

RADIUS_QUERY = """
SELECT vl.id, vl.title, vl.price, vl.year,
       mk.name AS make, mo.name AS model,
       ST_Distance(
           vl.geom,
           ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
       ) AS meters
FROM vehicle_listing vl
LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
WHERE ST_DWithin(
    vl.geom,
    ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
    %(radius_m)s
)
ORDER BY meters
LIMIT %(limit)s;
"""


@dataclass(frozen=True)
class UpsertResult:
    id: str
    listing: VehicleListing
    is_new: bool


def check_connection(dsn: str) -> bool:
    import psycopg

    with psycopg.connect(dsn) as conn:
        row = conn.execute("SELECT 1").fetchone()
    return row is not None and row[0] == 1


def seed_catalog(dsn: str) -> int:
    """Ensure schemas, catalog, and geo function exist; returns model row count."""
    import psycopg

    from notification_rake.storage.migrations import apply_layer_schema

    apply_layer_schema(dsn)
    with psycopg.connect(dsn) as conn:
        conn.execute(SEED_CATALOG)
        conn.execute(GEO_FUNCTION)
        row = conn.execute("SELECT COUNT(*) FROM vehicle_model").fetchone()
        conn.commit()
    return int(row[0]) if row else 0


def add_vehicle_model(dsn: str, make: str, model: str) -> int:
    """Insert make/model into catalog; returns model_id."""
    import psycopg

    sql_make = """
        INSERT INTO vehicle_make (name) VALUES (%(make)s)
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id;
    """
    sql_model = """
        INSERT INTO vehicle_model (make_id, name)
        VALUES (%(make_id)s, %(model)s)
        ON CONFLICT (make_id, name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id;
    """
    with psycopg.connect(dsn) as conn:
        make_row = conn.execute(sql_make, {"make": make}).fetchone()
        make_id = int(make_row[0])
        model_row = conn.execute(sql_model, {"make_id": make_id, "model": model}).fetchone()
        conn.commit()
    return int(model_row[0])


def upsert_listings(
    listings: list[VehicleListing],
    catalog: list[ModelRef],
    dsn: str,
) -> list[UpsertResult]:
    """Upsert listings using each item's longitude/latitude."""
    import psycopg

    results: list[UpsertResult] = []
    with psycopg.connect(dsn) as conn:
        for item in listings:
            if item.longitude is None or item.latitude is None:
                raise ValueError(
                    f"listing {item.source_listing_id} missing coordinates — "
                    "run geocode_listings first"
                )
            make_id, model_id = lookup_ids(item.make, item.model, catalog)
            row = conn.execute(
                UPSERT_LISTING,
                {
                    "source": item.source,
                    "source_listing_id": item.source_listing_id,
                    "title": item.title,
                    "make_id": make_id,
                    "model_id": model_id,
                    "year": item.year,
                    "price": item.price,
                    "country": item.country or country_for_source(item.source),
                    "lon": item.longitude,
                    "lat": item.latitude,
                },
            ).fetchone()
            if row:
                results.append(
                    UpsertResult(id=str(row[0]), listing=item, is_new=bool(row[1]))
                )
        conn.commit()
    return results


def search_within_radius(
    dsn: str,
    *,
    lon: float,
    lat: float,
    radius_m: float = 50_000,
    limit: int = 50,
) -> list[dict[str, Any]]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            RADIUS_QUERY,
            {"lon": lon, "lat": lat, "radius_m": radius_m, "limit": limit},
        ).fetchall()
    return [
        {
            "id": str(r[0]),
            "title": r[1],
            "price": float(r[2]) if r[2] is not None else None,
            "year": r[3],
            "make": r[4],
            "model": r[5],
            "meters": float(r[6]) if r[6] is not None else None,
        }
        for r in rows
    ]


def list_listings(
    dsn: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Paginated listings — delegates to search_listings."""
    from notification_rake.search import ListingSearch, search_listings

    return search_listings(dsn, ListingSearch(limit=limit, offset=offset))

"""Unified listing search — AutoTempest-style filters + Visor-style history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from notification_rake.analysis.import_rules import import_badges, import_year_cap
from notification_rake.models.ingest_routes import get_route, sources_for_route

SortKey = Literal[
    "updated_desc",
    "price_asc",
    "price_desc",
    "year_desc",
    "year_asc",
    "distance",
]

VALID_SORT: frozenset[str] = frozenset(
    {"updated_desc", "price_asc", "price_desc", "year_desc", "year_asc", "distance"}
)


@dataclass(frozen=True)
class ListingSearch:
    q: str | None = None
    make: str | None = None
    model: str | None = None
    source: str | None = None
    route: str | None = None
    country: str | None = None
    import_us: bool = False
    import_ca: bool = False
    year_min: int | None = None
    year_max: int | None = None
    price_min: float | None = None
    price_max: float | None = None
    lon: float | None = None
    lat: float | None = None
    radius_m: float | None = None
    sort: str = "updated_desc"
    limit: int = 24
    offset: int = 0


def _sort_clause(search: ListingSearch) -> str:
    sort = search.sort if search.sort in VALID_SORT else "updated_desc"
    if sort == "price_asc":
        return "vl.price ASC NULLS LAST, vl.updated_at DESC"
    if sort == "price_desc":
        return "vl.price DESC NULLS LAST, vl.updated_at DESC"
    if sort == "year_desc":
        return "vl.year DESC NULLS LAST, vl.updated_at DESC"
    if sort == "year_asc":
        return "vl.year ASC NULLS LAST, vl.updated_at DESC"
    if sort == "distance" and search.lon is not None and search.lat is not None:
        return "meters ASC NULLS LAST"
    return "vl.updated_at DESC"


def _build_search_sql(search: ListingSearch) -> tuple[str, str, dict[str, Any]]:
    """Return SELECT body, WHERE clause, params."""
    params: dict[str, Any] = {"limit": search.limit, "offset": search.offset}
    where = ["TRUE"]

    if search.q:
        params["q"] = f"%{search.q.strip()}%"
        where.append(
            "(vl.title ILIKE %(q)s OR mk.name ILIKE %(q)s OR mo.name ILIKE %(q)s "
            "OR vl.source_listing_id ILIKE %(q)s)"
        )
    if search.make:
        params["make"] = search.make.strip()
        where.append("mk.name ILIKE %(make)s")
    if search.model:
        params["model"] = search.model.strip()
        where.append("mo.name ILIKE %(model)s")
    if search.source:
        params["source"] = search.source.strip()
        where.append("vl.source = %(source)s")
    elif search.route:
        route_sources = sources_for_route(search.route.strip())
        if route_sources:
            params["route_sources"] = list(route_sources)
            where.append("vl.source = ANY(%(route_sources)s)")
        else:
            route = get_route(search.route)
            if route and route.country:
                params["route_country"] = route.country
                where.append("vl.country = %(route_country)s")
    if search.country:
        params["country"] = search.country.strip().upper()
        where.append("vl.country = %(country)s")
    import_cap = import_year_cap(import_us=search.import_us, import_ca=search.import_ca)
    if import_cap is not None:
        params["import_year_cap"] = import_cap
        where.append("vl.year IS NOT NULL AND vl.year <= %(import_year_cap)s")
    if search.year_min is not None:
        params["year_min"] = search.year_min
        where.append("vl.year >= %(year_min)s")
    if search.year_max is not None:
        params["year_max"] = search.year_max
        where.append("vl.year <= %(year_max)s")
    if search.price_min is not None:
        params["price_min"] = search.price_min
        where.append("vl.price >= %(price_min)s")
    if search.price_max is not None:
        params["price_max"] = search.price_max
        where.append("vl.price <= %(price_max)s")
    if search.lon is not None and search.lat is not None and search.radius_m:
        params["lon"] = search.lon
        params["lat"] = search.lat
        params["radius_m"] = search.radius_m
        where.append(
            "ST_DWithin(vl.geom, "
            "ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, %(radius_m)s)"
        )

    distance_select = "NULL::double precision AS meters"
    if search.lon is not None and search.lat is not None:
        params["lon"] = search.lon
        params["lat"] = search.lat
        distance_select = """
            ST_Distance(
                vl.geom,
                ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography
            ) AS meters
        """

    select = f"""
        SELECT vl.id, vl.title, vl.price, vl.year, vl.source, vl.source_listing_id,
               vl.country, mk.name AS make, mo.name AS model,
               ST_Y(vl.geom::geometry) AS lat,
               ST_X(vl.geom::geometry) AS lon,
               vl.updated_at,
               {distance_select},
               hist.first_price,
               hist.price_events,
               img.url AS thumbnail_url
        FROM vehicle_listing vl
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        LEFT JOIN LATERAL (
            SELECT li.url
            FROM listings.listing_image li
            JOIN listings.listing rl ON rl.id = li.listing_id
            JOIN listings.source src ON src.id = rl.source_id
            WHERE rl.external_id = vl.source_listing_id AND src.name = vl.source
            ORDER BY li.position
            LIMIT 1
        ) img ON TRUE
        LEFT JOIN LATERAL (
            SELECT
                (SELECT lh.price FROM listings.listing_history lh
                 JOIN listings.listing rl ON rl.id = lh.listing_id
                 JOIN listings.source src ON src.id = rl.source_id
                 WHERE rl.external_id = vl.source_listing_id AND src.name = vl.source
                 ORDER BY lh.recorded_at ASC LIMIT 1) AS first_price,
                (SELECT COUNT(*) FROM listings.listing_history lh
                 JOIN listings.listing rl ON rl.id = lh.listing_id
                 JOIN listings.source src ON src.id = rl.source_id
                 WHERE rl.external_id = vl.source_listing_id
                   AND src.name = vl.source) AS price_events
        ) hist ON TRUE
    """
    where_sql = " AND ".join(where)
    return select, where_sql, params


def _row_to_item(row: tuple[Any, ...]) -> dict[str, Any]:
    price = float(row[2]) if row[2] is not None else None
    first_price = float(row[13]) if row[13] is not None else None
    price_delta = None
    if price is not None and first_price is not None and first_price != price:
        price_delta = price - first_price
    thumb = row[15] if len(row) > 15 else None
    year = row[3]
    badges = import_badges(year)
    return {
        "id": str(row[0]),
        "title": row[1],
        "price": price,
        "year": year,
        "source": row[4],
        "source_listing_id": row[5],
        "country": row[6],
        "make": row[7],
        "model": row[8],
        "lat": float(row[9]) if row[9] is not None else None,
        "lon": float(row[10]) if row[10] is not None else None,
        "updated_at": row[11].isoformat() if row[11] else None,
        "meters": float(row[12]) if row[12] is not None else None,
        "first_price": first_price,
        "price_delta": price_delta,
        "price_events": int(row[14] or 0),
        "thumbnail_url": thumb,
        "import_badges": badges,
    }


def search_listings_postgres(
    dsn: str, search: ListingSearch
) -> tuple[list[dict[str, Any]], int]:
    import psycopg

    select, where_sql, params = _build_search_sql(search)
    order = _sort_clause(search)
    count_sql = f"""
        SELECT COUNT(*) FROM vehicle_listing vl
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        WHERE {where_sql}
    """
    data_sql = f"{select} WHERE {where_sql} ORDER BY {order} LIMIT %(limit)s OFFSET %(offset)s"

    with psycopg.connect(dsn) as conn:
        total_row = conn.execute(count_sql, params).fetchone()
        rows = conn.execute(data_sql, params).fetchall()

    total = int(total_row[0]) if total_row else 0
    return [_row_to_item(r) for r in rows], total


def enrich_listings_by_ids(
    dsn: str,
    listing_ids: list[str],
    search: ListingSearch,
) -> list[dict[str, Any]]:
    """Fetch full listing rows from Postgres, preserving Meilisearch hit order."""
    import psycopg

    if not listing_ids:
        return []
    select, _, params = _build_search_sql(search)
    params["ids"] = listing_ids
    sql = f"""
        {select}
        WHERE vl.id = ANY(%(ids)s::uuid[])
    """
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, params).fetchall()
    by_id: dict[str, dict[str, Any]] = {}
    for r in rows:
        item = _row_to_item(r)
        by_id[item["id"]] = item
    return [by_id[i] for i in listing_ids if i in by_id]


def search_listings(dsn: str, search: ListingSearch) -> tuple[list[dict[str, Any]], int]:
    import logging

    from notification_rake.config import settings
    from notification_rake.search import meilisearch_client as meili

    if meili.meilisearch_enabled():
        try:
            return meili.search_listings(dsn, search)
        except Exception:
            if settings.search_engine == "meilisearch":
                raise
            logging.getLogger(__name__).warning(
                "Meilisearch unavailable — falling back to Postgres",
                exc_info=True,
            )
    return search_listings_postgres(dsn, search)


def get_listing_detail(dsn: str, listing_id: str) -> dict[str, Any] | None:
    import psycopg

    from notification_rake.storage.auction import (
        auction_detail_for_listing,
        list_images_for_listing,
    )
    from notification_rake.web.media_proxy import proxy_url_for

    sql = """
        SELECT vl.id, vl.title, vl.price, vl.year, vl.source, vl.source_listing_id,
               vl.description, vl.country, mk.name, mo.name,
               ST_Y(vl.geom::geometry), ST_X(vl.geom::geometry), vl.updated_at,
               rl.url, rl.raw_payload
        FROM vehicle_listing vl
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        LEFT JOIN listings.source src ON src.name = vl.source
        LEFT JOIN listings.listing rl ON rl.external_id = vl.source_listing_id
            AND rl.source_id = src.id
        WHERE vl.id = %(id)s;
    """
    history_sql = """
        SELECT lh.price, lh.title, lh.recorded_at
        FROM listings.listing_history lh
        JOIN listings.listing rl ON rl.id = lh.listing_id
        JOIN listings.source src ON src.id = rl.source_id
        JOIN vehicle_listing vl ON vl.source_listing_id = rl.external_id AND vl.source = src.name
        WHERE vl.id = %(id)s
        ORDER BY lh.recorded_at ASC;
    """
    with psycopg.connect(dsn) as conn:
        row = conn.execute(sql, {"id": listing_id}).fetchone()
        if not row:
            return None
        hist = conn.execute(history_sql, {"id": listing_id}).fetchall()

    images = list_images_for_listing(dsn, listing_id)
    image_payload = [
        {"url": img["url"], "proxy_url": proxy_url_for(img["url"]), "position": img["position"]}
        for img in images
    ]
    auction = auction_detail_for_listing(dsn, listing_id)
    raw_payload = row[14] if len(row) > 14 else None
    meta = {}
    if isinstance(raw_payload, dict):
        meta = raw_payload.get("metadata") or {}
    elif raw_payload:
        import json

        try:
            meta = json.loads(raw_payload).get("metadata") or {}
        except (TypeError, json.JSONDecodeError):
            meta = {}

    badges = (auction or {}).get("badges") or meta.get("badges") or []
    badges = list(dict.fromkeys([*badges, *import_badges(row[3])]))
    outbound = (
        row[13]
        or meta.get("copart_url")
        or meta.get("source_url")
        or meta.get("item_web_url")
    )
    proxy_links = meta.get("proxy_links") or {}

    return {
        "id": str(row[0]),
        "title": row[1],
        "price": float(row[2]) if row[2] is not None else None,
        "year": row[3],
        "source": row[4],
        "source_listing_id": row[5],
        "description": row[6],
        "country": row[7],
        "make": row[8],
        "model": row[9],
        "lat": float(row[10]) if row[10] is not None else None,
        "lon": float(row[11]) if row[11] is not None else None,
        "updated_at": row[12].isoformat() if row[12] else None,
        "outbound_url": outbound,
        "images": image_payload,
        "auction": auction,
        "badges": badges,
        "proxy_links": proxy_links,
        "price_history": [
            {
                "price": float(h[0]) if h[0] is not None else None,
                "title": h[1],
                "recorded_at": h[2].isoformat() if h[2] else None,
            }
            for h in hist
        ],
    }


def search_facets(dsn: str, search: ListingSearch) -> dict[str, Any]:
    import psycopg

    _, where_sql, params = _build_search_sql(search)
    base = f"""
        FROM vehicle_listing vl
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        WHERE {where_sql}
    """
    with psycopg.connect(dsn) as conn:
        sources = conn.execute(
            f"SELECT vl.source, COUNT(*) {base} GROUP BY vl.source ORDER BY COUNT(*) DESC",
            params,
        ).fetchall()
        makes = conn.execute(
            f"SELECT mk.name, COUNT(*) {base} AND mk.name IS NOT NULL "
            "GROUP BY mk.name ORDER BY COUNT(*) DESC LIMIT 20",
            params,
        ).fetchall()
        countries = conn.execute(
            f"SELECT vl.country, COUNT(*) {base} AND vl.country IS NOT NULL "
            "GROUP BY vl.country ORDER BY COUNT(*) DESC",
            params,
        ).fetchall()
    return {
        "sources": [{"name": r[0], "count": int(r[1])} for r in sources],
        "makes": [{"name": r[0], "count": int(r[1])} for r in makes],
        "countries": [{"code": r[0], "count": int(r[1])} for r in countries],
    }


def list_regions(dsn: str) -> list[dict[str, Any]]:
    import psycopg

    from notification_rake.models.regions import REGION_LABELS

    sql = """
        SELECT country, COUNT(*) AS cnt
        FROM vehicle_listing
        WHERE country IS NOT NULL
        GROUP BY country
        ORDER BY cnt DESC;
    """
    try:
        with psycopg.connect(dsn) as conn:
            rows = conn.execute(sql).fetchall()
    except Exception:
        return []
    return [
        {
            "code": r[0],
            "label": REGION_LABELS.get(r[0], r[0]),
            "count": int(r[1]),
        }
        for r in rows
    ]


def market_summary(dsn: str) -> dict[str, Any]:
    import psycopg

    sql = """
        SELECT source,
               COUNT(*) AS listings,
               ROUND(AVG(price)::numeric, 0) AS avg_price,
               MIN(price) AS min_price,
               MAX(price) AS max_price
        FROM vehicle_listing
        WHERE price IS NOT NULL
        GROUP BY source
        ORDER BY listings DESC;
    """
    try:
        with psycopg.connect(dsn) as conn:
            rows = conn.execute(sql).fetchall()
    except Exception:
        return {"by_source": [], "total": 0}
    by_source = [
        {
            "source": r[0],
            "listings": int(r[1]),
            "avg_price": float(r[2]) if r[2] is not None else None,
            "min_price": float(r[3]) if r[3] is not None else None,
            "max_price": float(r[4]) if r[4] is not None else None,
        }
        for r in rows
    ]
    total = sum(item["listings"] for item in by_source)
    return {"by_source": by_source, "total": total}


def list_ingest_routes(dsn: str) -> list[dict[str, Any]]:
    """Route catalog with live listing counts for search/ingest UI."""
    import psycopg

    from notification_rake.models.ingest_routes import list_routes

    routes = [r for r in list_routes(include_connected=False) if r.sources]
    if not routes:
        return []
    sql = """
        SELECT source, COUNT(*) FROM vehicle_listing
        WHERE source = ANY(%(sources)s)
        GROUP BY source;
    """
    all_sources = sorted({s for r in routes for s in r.sources})
    try:
        with psycopg.connect(dsn) as conn:
            rows = conn.execute(sql, {"sources": all_sources}).fetchall()
    except Exception:
        rows = []
    counts = {r[0]: int(r[1]) for r in rows}
    return [
        {
            "slug": route.slug,
            "label": route.label,
            "country": route.country,
            "sources": sorted(route.sources),
            "description": route.description,
            "listings": sum(counts.get(s, 0) for s in route.sources),
        }
        for route in routes
    ]

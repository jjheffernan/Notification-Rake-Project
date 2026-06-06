"""Meilisearch index sync and query — optional search engine layer."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from notification_rake.analysis.import_rules import import_year_cap
from notification_rake.config import settings
from notification_rake.models.ingest_routes import sources_for_route
from notification_rake.search.service import ListingSearch

logger = logging.getLogger(__name__)

LISTINGS_INDEX = "listings"

_INDEX_SETTINGS = {
    "searchableAttributes": [
        "title",
        "make",
        "model",
        "source_listing_id",
        "source",
    ],
    "filterableAttributes": [
        "source",
        "make",
        "model",
        "year",
        "price",
        "country",
        "_geo",
    ],
    "sortableAttributes": ["price", "year", "updated_at"],
}


def meilisearch_enabled() -> bool:
    if not settings.meilisearch_url:
        return False
    return settings.search_engine in {"auto", "meilisearch"}


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.meilisearch_api_key:
        headers["Authorization"] = f"Bearer {settings.meilisearch_api_key}"
    return headers


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.meilisearch_url.rstrip("/"),
        headers=_headers(),
        timeout=10.0,
    )


def check_health() -> tuple[bool, str]:
    if not settings.meilisearch_url:
        return False, "MEILISEARCH_URL not set"
    try:
        with _client() as client:
            resp = client.get("/health")
            resp.raise_for_status()
            return True, resp.text.strip()
    except Exception as exc:
        return False, str(exc)


def ensure_index() -> None:
    with _client() as client:
        resp = client.post(f"/indexes/{LISTINGS_INDEX}", json={"uid": LISTINGS_INDEX})
        if resp.status_code not in (201, 202, 409):
            resp.raise_for_status()
        settings_resp = client.patch(
            f"/indexes/{LISTINGS_INDEX}/settings",
            json=_INDEX_SETTINGS,
        )
        settings_resp.raise_for_status()


def _build_filters(search: ListingSearch) -> list[str]:
    filters: list[str] = []
    if search.make:
        filters.append(f'make = "{search.make.strip()}"')
    if search.model:
        filters.append(f'model = "{search.model.strip()}"')
    if search.source:
        filters.append(f'source = "{search.source.strip()}"')
    elif search.route:
        route_sources = sources_for_route(search.route.strip())
        if route_sources:
            quoted = ", ".join(f'"{s}"' for s in sorted(route_sources))
            filters.append(f"source IN [{quoted}]")
    if search.country:
        filters.append(f'country = "{search.country.strip().upper()}"')
    import_cap = import_year_cap(import_us=search.import_us, import_ca=search.import_ca)
    if import_cap is not None:
        filters.append(f"year <= {import_cap}")
    if search.year_min is not None:
        filters.append(f"year >= {search.year_min}")
    if search.year_max is not None:
        filters.append(f"year <= {search.year_max}")
    if search.price_min is not None:
        filters.append(f"price >= {search.price_min}")
    if search.price_max is not None:
        filters.append(f"price <= {search.price_max}")
    if search.lon is not None and search.lat is not None and search.radius_m:
        filters.append(
            f"_geoRadius({search.lat}, {search.lon}, {int(search.radius_m)})"
        )
    return filters


def _sort_for(search: ListingSearch) -> list[str]:
    sort = search.sort if search.sort in {
        "updated_desc",
        "price_asc",
        "price_desc",
        "year_desc",
        "year_asc",
        "distance",
    } else "updated_desc"
    if sort == "distance" and search.lon is not None and search.lat is not None:
        return [f"_geoPoint({search.lat}, {search.lon}):asc"]
    mapping = {
        "updated_desc": ["updated_at:desc"],
        "price_asc": ["price:asc"],
        "price_desc": ["price:desc"],
        "year_desc": ["year:desc"],
        "year_asc": ["year:asc"],
    }
    return mapping.get(sort, ["updated_at:desc"])


def _document_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    lat = float(row[9]) if row[9] is not None else None
    lon = float(row[10]) if row[10] is not None else None
    updated_at = row[11]
    doc: dict[str, Any] = {
        "id": str(row[0]),
        "title": row[1],
        "price": float(row[2]) if row[2] is not None else None,
        "year": row[3],
        "source": row[4],
        "source_listing_id": row[5],
        "country": row[6],
        "make": row[7],
        "model": row[8],
        "updated_at": int(updated_at.timestamp()) if updated_at else 0,
    }
    if lat is not None and lon is not None:
        doc["_geo"] = {"lat": lat, "lng": lon}
    return doc


def sync_documents(dsn: str, listing_ids: list[str] | None = None) -> int:
    import psycopg

    if not meilisearch_enabled():
        return 0
    if listing_ids is not None and not listing_ids:
        return 0
    ensure_index()
    if listing_ids:
        sql = """
            SELECT vl.id, vl.title, vl.price, vl.year, vl.source, vl.source_listing_id,
                   vl.country, mk.name AS make, mo.name AS model,
                   ST_Y(vl.geom::geometry) AS lat,
                   ST_X(vl.geom::geometry) AS lon,
                   vl.updated_at
            FROM vehicle_listing vl
            LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
            LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
            WHERE vl.id = ANY(%(ids)s::uuid[])
        """
        params: dict[str, Any] = {"ids": listing_ids}
    else:
        sql = """
            SELECT vl.id, vl.title, vl.price, vl.year, vl.source, vl.source_listing_id,
                   vl.country, mk.name AS make, mo.name AS model,
                   ST_Y(vl.geom::geometry) AS lat,
                   ST_X(vl.geom::geometry) AS lon,
                   vl.updated_at
            FROM vehicle_listing vl
            LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
            LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        """
        params = {}
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, params).fetchall()
    documents = [_document_from_row(row) for row in rows]
    if not documents:
        return 0
    with _client() as client:
        resp = client.post(
            f"/indexes/{LISTINGS_INDEX}/documents",
            json=documents,
            params={"primaryKey": "id"},
        )
        resp.raise_for_status()
    return len(documents)


def search_documents(search: ListingSearch) -> tuple[list[str], int]:
    body: dict[str, Any] = {
        "q": search.q or "",
        "limit": search.limit,
        "offset": search.offset,
        "sort": _sort_for(search),
    }
    filters = _build_filters(search)
    if filters:
        body["filter"] = filters
    with _client() as client:
        resp = client.post(f"/indexes/{LISTINGS_INDEX}/search", json=body)
        resp.raise_for_status()
        data = resp.json()
    hits = data.get("hits") or []
    ids = [str(hit["id"]) for hit in hits if hit.get("id")]
    total = int(data.get("estimatedTotalHits") or data.get("totalHits") or len(ids))
    return ids, total


def search_listings(dsn: str, search: ListingSearch) -> tuple[list[dict[str, Any]], int]:
    ids, total = search_documents(search)
    if not ids:
        return [], total
    from notification_rake.search.service import enrich_listings_by_ids

    items = enrich_listings_by_ids(dsn, ids, search)
    return items, total

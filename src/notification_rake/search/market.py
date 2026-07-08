"""Make/model market analytics — classic.com-style data views."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from notification_rake.analysis.import_rules import import_badges


def slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def slug_to_label(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)


@dataclass(frozen=True)
class ModelMarketQuery:
    make: str
    model: str
    year_min: int | None = None
    year_max: int | None = None
    source: str | None = None
    country: str | None = None
    period_months: int | None = 12
    min_price: float | None = None
    max_price: float | None = None
    max_mileage: int | None = None
    sale_status: str | None = None


def classify_sale_status(
    auction_status: str | None,
    *,
    price_events: int = 0,
) -> str:
    """Map listing/auction state to classic.com-style chart categories."""
    status = (auction_status or "").lower()
    if status in {"sold", "ended"}:
        return "sold"
    if status in {"live", "active", "upcoming", "on_approval"}:
        return "high_bid"
    if price_events > 1:
        return "last_asking"
    return "for_sale"


def compute_moving_average(
    points: list[dict[str, Any]],
    *,
    status: str = "sold",
    window_months: int = 3,
) -> list[dict[str, Any]]:
    """Monthly rolling average price for scatter chart trend line."""
    from collections import defaultdict
    from datetime import datetime

    filtered = [p for p in points if p.get("status") == status and p.get("price") is not None]
    if not filtered:
        filtered = [p for p in points if p.get("price") is not None]
    if not filtered:
        return []

    monthly: dict[str, list[float]] = defaultdict(list)
    for point in filtered:
        raw = point.get("date") or ""
        month_key = raw[:7] if len(raw) >= 7 else raw
        if month_key:
            monthly[month_key].append(float(point["price"]))

    months = sorted(monthly)
    monthly_avg = [(m, sum(monthly[m]) / len(monthly[m])) for m in months]
    if not monthly_avg:
        return []

    result: list[dict[str, Any]] = []
    for idx, (month, _) in enumerate(monthly_avg):
        start = max(0, idx - window_months + 1)
        window = monthly_avg[start : idx + 1]
        avg = sum(v for _, v in window) / len(window)
        dt = datetime.strptime(f"{month}-01", "%Y-%m-%d")
        result.append({"date": dt.date().isoformat(), "avg_price": round(avg, 2)})
    return result


def _sales_kpis(points: list[dict[str, Any]]) -> dict[str, Any]:
    sold = [p for p in points if p.get("status") == "sold" and p.get("price") is not None]
    basis = sold or [p for p in points if p.get("price") is not None]
    if not basis:
        return {
            "avg_price": None,
            "sales_count": 0,
            "dollar_volume": None,
            "lowest_sale": None,
            "top_sale": None,
            "most_recent": None,
            "most_recent_date": None,
        }
    prices = [float(p["price"]) for p in basis]
    most_recent_pt = max(basis, key=lambda p: p.get("date") or "")
    return {
        "avg_price": round(sum(prices) / len(prices), 2),
        "sales_count": len(basis),
        "dollar_volume": round(sum(prices), 2),
        "lowest_sale": min(prices),
        "top_sale": max(prices),
        "most_recent": float(most_recent_pt["price"]),
        "most_recent_date": most_recent_pt.get("date"),
    }


def _model_where(query: ModelMarketQuery) -> tuple[str, dict[str, Any]]:
    make_label = query.make.strip()
    model_label = query.model.strip()
    params: dict[str, Any] = {
        "make": make_label,
        "model": model_label,
        "title_pat": f"%{make_label}%{model_label}%",
    }
    where = [
        "("
        "(mk.name ILIKE %(make)s AND mo.name ILIKE %(model)s) "
        "OR vl.title ILIKE %(title_pat)s"
        ")"
    ]
    if query.year_min is not None:
        params["year_min"] = query.year_min
        where.append("vl.year >= %(year_min)s")
    if query.year_max is not None:
        params["year_max"] = query.year_max
        where.append("vl.year <= %(year_max)s")
    if query.source:
        params["source"] = query.source.strip()
        where.append("vl.source = %(source)s")
    if query.country:
        params["country"] = query.country.strip().upper()
        where.append("vl.country = %(country)s")
    if query.min_price is not None:
        params["min_price"] = query.min_price
        where.append("vl.price >= %(min_price)s")
    if query.max_price is not None:
        params["max_price"] = query.max_price
        where.append("vl.price <= %(max_price)s")
    if query.max_mileage is not None:
        params["max_mileage"] = query.max_mileage
        where.append("vl.mileage <= %(max_mileage)s")
    return " AND ".join(where), params


def _fetch_sales_points(
    conn: Any,
    where_sql: str,
    params: dict[str, Any],
    *,
    period_months: int | None,
) -> list[dict[str, Any]]:
    period_clause = ""
    query_params = dict(params)
    if period_months is not None:
        period_clause = (
            " AND COALESCE(al.ends_at, rl.updated_at, vl.updated_at, vl.created_at) "
            ">= NOW() - make_interval(months => %(period_months)s)"
        )
        query_params["period_months"] = period_months

    sql = f"""
        SELECT
            vl.id,
            vl.title,
            vl.price,
            vl.year,
            vl.mileage,
            vl.source,
            vl.country,
            COALESCE(al.ends_at, rl.updated_at, vl.updated_at, vl.created_at) AS event_at,
            al.auction_status,
            COALESCE(hist.price_events, 0) AS price_events
        FROM vehicle_listing vl
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        LEFT JOIN listings.source src ON src.name = vl.source
        LEFT JOIN listings.listing rl
            ON rl.source_id = src.id AND rl.external_id = vl.source_listing_id
        LEFT JOIN listings.auction_lot al ON al.listing_id = rl.id
        LEFT JOIN LATERAL (
            SELECT COUNT(*)::int AS price_events
            FROM listings.listing_history lh
            WHERE lh.listing_id = rl.id
        ) hist ON TRUE
        WHERE {where_sql}
          AND vl.price IS NOT NULL
          {period_clause}
        ORDER BY event_at ASC;
    """
    rows = conn.execute(sql, query_params).fetchall()
    points: list[dict[str, Any]] = []
    for row in rows:
        status = classify_sale_status(row[8], price_events=int(row[9] or 0))
        event_at = row[7]
        points.append(
            {
                "id": str(row[0]),
                "title": row[1],
                "price": float(row[2]) if row[2] is not None else None,
                "year": row[3],
                "mileage": row[4],
                "source": row[5],
                "country": row[6],
                "date": event_at.date().isoformat() if event_at else None,
                "status": status,
            }
        )
    return points


def list_model_markets(dsn: str, *, limit: int = 100) -> list[dict[str, Any]]:
    """Catalog-index of make/model pairs with listing counts and price stats."""
    import psycopg

    sql = """
        SELECT
            COALESCE(mk.name, 'Unknown') AS make,
            COALESCE(mo.name, 'Unknown') AS model,
            COUNT(*) AS listings,
            ROUND(AVG(vl.price)::numeric, 0) AS avg_price,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY vl.price) AS median_price,
            MIN(vl.price) AS min_price,
            MAX(vl.price) AS max_price,
            MIN(vl.year) AS year_min,
            MAX(vl.year) AS year_max
        FROM vehicle_listing vl
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        WHERE vl.price IS NOT NULL
          AND (mk.name IS NOT NULL OR mo.name IS NOT NULL)
        GROUP BY mk.name, mo.name
        HAVING COUNT(*) >= 1
        ORDER BY COUNT(*) DESC, mk.name, mo.name
        LIMIT %(limit)s;
    """
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, {"limit": limit}).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        make, model = str(row[0]), str(row[1])
        if make == "Unknown" and model == "Unknown":
            continue
        results.append(
            {
                "make": make,
                "model": model,
                "make_slug": slugify(make),
                "model_slug": slugify(model),
                "listings": int(row[2]),
                "avg_price": float(row[3]) if row[3] is not None else None,
                "median_price": float(row[4]) if row[4] is not None else None,
                "min_price": float(row[5]) if row[5] is not None else None,
                "max_price": float(row[6]) if row[6] is not None else None,
                "year_min": row[7],
                "year_max": row[8],
                "url": f"/m/{slugify(make)}/{slugify(model)}",
            }
        )
    return results


def model_market_detail(dsn: str, query: ModelMarketQuery) -> dict[str, Any] | None:
    """Full market snapshot for one make/model — stats, breakdowns, comps."""
    import psycopg

    where_sql, params = _model_where(query)
    base_from = f"""
        FROM vehicle_listing vl
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        WHERE {where_sql}
    """
    summary_sql = f"""
        SELECT
            COUNT(*) AS listings,
            COUNT(*) FILTER (WHERE vl.price IS NOT NULL) AS priced,
            ROUND(AVG(vl.price)::numeric, 0) AS avg_price,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY vl.price) AS median_price,
            MIN(vl.price) AS min_price,
            MAX(vl.price) AS max_price,
            MIN(vl.year) AS year_min,
            MAX(vl.year) AS year_max,
            ROUND(AVG(vl.mileage)::numeric, 0) AS avg_mileage
        {base_from};
    """
    by_year_sql = f"""
        SELECT vl.year,
               COUNT(*) AS listings,
               ROUND(AVG(vl.price)::numeric, 0) AS avg_price,
               MIN(vl.price) AS min_price,
               MAX(vl.price) AS max_price
        {base_from} AND vl.year IS NOT NULL AND vl.price IS NOT NULL
        GROUP BY vl.year
        ORDER BY vl.year DESC;
    """
    by_source_sql = f"""
        SELECT vl.source,
               COUNT(*) AS listings,
               ROUND(AVG(vl.price)::numeric, 0) AS avg_price
        {base_from}
        GROUP BY vl.source
        ORDER BY COUNT(*) DESC;
    """
    by_country_sql = f"""
        SELECT vl.country,
               COUNT(*) AS listings,
               ROUND(AVG(vl.price)::numeric, 0) AS avg_price
        {base_from} AND vl.country IS NOT NULL
        GROUP BY vl.country
        ORDER BY COUNT(*) DESC;
    """
    comps_sql = f"""
        SELECT vl.id, vl.title, vl.price, vl.year, vl.source, vl.country,
               mk.name, mo.name, vl.updated_at,
               hist.first_price, hist.price_events
        {base_from}
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
        ORDER BY vl.updated_at DESC
        LIMIT 50;
    """
    trend_sql = """
        SELECT date_trunc('month', lh.recorded_at)::date AS month,
               ROUND(AVG(lh.price)::numeric, 0) AS avg_price,
               COUNT(DISTINCT vl.id) AS listings
        FROM listings.listing_history lh
        JOIN listings.listing rl ON rl.id = lh.listing_id
        JOIN listings.source src ON src.id = rl.source_id
        JOIN vehicle_listing vl ON vl.source_listing_id = rl.external_id AND vl.source = src.name
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        WHERE (
            (mk.name ILIKE %(make)s AND mo.name ILIKE %(model)s)
            OR vl.title ILIKE %(title_pat)s
        )
        GROUP BY 1
        HAVING COUNT(*) >= 1
        ORDER BY 1;
    """
    new_listings_sql = f"""
        SELECT date_trunc('month', vl.created_at)::date AS month,
               COUNT(*) AS new_listings
        {base_from}
        GROUP BY 1
        ORDER BY 1;
    """
    activity_sql = """
        SELECT date_trunc('month', lh.recorded_at)::date AS month,
               COUNT(*) AS price_events,
               COUNT(DISTINCT vl.id) AS active_listings
        FROM listings.listing_history lh
        JOIN listings.listing rl ON rl.id = lh.listing_id
        JOIN listings.source src ON src.id = rl.source_id
        JOIN vehicle_listing vl ON vl.source_listing_id = rl.external_id AND vl.source = src.name
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        WHERE (
            (mk.name ILIKE %(make)s AND mo.name ILIKE %(model)s)
            OR vl.title ILIKE %(title_pat)s
        )
        GROUP BY 1
        ORDER BY 1;
    """

    with psycopg.connect(dsn) as conn:
        summary = conn.execute(summary_sql, params).fetchone()
        if not summary or int(summary[0]) == 0:
            return None
        by_year = conn.execute(by_year_sql, params).fetchall()
        by_source = conn.execute(by_source_sql, params).fetchall()
        by_country = conn.execute(by_country_sql, params).fetchall()
        comps = conn.execute(comps_sql, params).fetchall()
        trend = conn.execute(trend_sql, params).fetchall()
        new_listings = conn.execute(new_listings_sql, params).fetchall()
        activity = conn.execute(activity_sql, params).fetchall()
        sales_points = _fetch_sales_points(
            conn, where_sql, params, period_months=query.period_months
        )

    if query.sale_status:
        sales_points = [p for p in sales_points if p["status"] == query.sale_status]

    moving_average = compute_moving_average(sales_points)
    sales_kpis = _sales_kpis(sales_points)

    make_name = query.make.strip()
    model_name = query.model.strip()
    comp_rows: list[dict[str, Any]] = []
    for row in comps:
        price = float(row[2]) if row[2] is not None else None
        first_price = float(row[9]) if row[9] is not None else None
        delta = price - first_price if price is not None and first_price is not None else None
        year = row[3]
        comp_rows.append(
            {
                "id": str(row[0]),
                "title": row[1],
                "price": price,
                "year": year,
                "source": row[4],
                "country": row[5],
                "make": row[6],
                "model": row[7],
                "updated_at": row[8].isoformat() if row[8] else None,
                "first_price": first_price,
                "price_delta": delta,
                "price_events": int(row[10] or 0),
                "import_badges": import_badges(year),
            }
        )

    return {
        "make": make_name,
        "model": model_name,
        "make_slug": slugify(make_name),
        "model_slug": slugify(model_name),
        "summary": {
            "listings": int(summary[0]),
            "priced": int(summary[1] or 0),
            "avg_price": float(summary[2]) if summary[2] is not None else None,
            "median_price": float(summary[3]) if summary[3] is not None else None,
            "min_price": float(summary[4]) if summary[4] is not None else None,
            "max_price": float(summary[5]) if summary[5] is not None else None,
            "year_min": summary[6],
            "year_max": summary[7],
            "avg_mileage": int(summary[8]) if summary[8] is not None else None,
        },
        "by_year": [
            {
                "year": int(r[0]),
                "listings": int(r[1]),
                "avg_price": float(r[2]) if r[2] is not None else None,
                "min_price": float(r[3]) if r[3] is not None else None,
                "max_price": float(r[4]) if r[4] is not None else None,
            }
            for r in by_year
        ],
        "by_source": [
            {
                "source": r[0],
                "listings": int(r[1]),
                "avg_price": float(r[2]) if r[2] is not None else None,
            }
            for r in by_source
        ],
        "by_country": [
            {
                "country": r[0],
                "listings": int(r[1]),
                "avg_price": float(r[2]) if r[2] is not None else None,
            }
            for r in by_country
        ],
        "price_trend": [
            {
                "month": r[0].isoformat() if r[0] else None,
                "avg_price": float(r[1]) if r[1] is not None else None,
                "listings": int(r[2]),
            }
            for r in trend
        ],
        "sales_volume": {
            "internal": {
                "inventory_by_year": [
                    {
                        "year": int(r[0]),
                        "listings": int(r[1]),
                    }
                    for r in by_year
                ],
                "new_listings_by_month": [
                    {
                        "month": r[0].isoformat() if r[0] else None,
                        "new_listings": int(r[1]),
                    }
                    for r in new_listings
                ],
                "activity_by_month": [
                    {
                        "month": r[0].isoformat() if r[0] else None,
                        "price_events": int(r[1]),
                        "active_listings": int(r[2]),
                    }
                    for r in activity
                ],
                "total_indexed": int(summary[0]),
                "active_sources": len(by_source),
            },
            "external": _fetch_external_volume(make_name, model_name),
        },
        "comps": comp_rows,
        "sales_analytics": {
            "kpis": sales_kpis,
            "points": sales_points,
            "moving_average": moving_average,
            "filters": {
                "period_months": query.period_months,
                "countries": sorted({p["country"] for p in sales_points if p.get("country")}),
                "sources": sorted({p["source"] for p in sales_points if p.get("source")}),
            },
        },
    }


def _fetch_external_volume(make: str, model: str) -> dict[str, Any]:
    try:
        from notification_rake.integrations.market_external import fetch_external_volume_data

        return fetch_external_volume_data(make, model)
    except Exception:
        return {
            "us_market_trend": [],
            "production": None,
            "epa": None,
            "nhtsa": None,
            "brand_us_sales": None,
            "model_regional_rank": None,
            "sources_fetched": [],
            "sources_skipped": [{"source": "external", "reason": "fetch failed"}],
        }


def resolve_model_from_slugs(dsn: str, make_slug: str, model_slug: str) -> ModelMarketQuery | None:
    """Resolve URL slugs to canonical make/model labels from catalog data."""
    import psycopg

    make_guess = slug_to_label(make_slug)
    model_guess = slug_to_label(model_slug)
    sql = """
        SELECT DISTINCT mk.name, mo.name
        FROM vehicle_listing vl
        LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
        LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
        WHERE (
            (LOWER(REPLACE(mk.name, ' ', '-')) = %(make_slug)s
             AND LOWER(REPLACE(mo.name, ' ', '-')) = %(model_slug)s)
            OR (mk.name ILIKE %(make)s AND mo.name ILIKE %(model)s)
            OR vl.title ILIKE %(title_pat)s
        )
        ORDER BY mk.name NULLS LAST, mo.name NULLS LAST
        LIMIT 1;
    """
    params = {
        "make_slug": make_slug.lower(),
        "model_slug": model_slug.lower(),
        "make": make_guess,
        "model": model_guess,
        "title_pat": f"%{make_guess}%{model_guess}%",
    }
    with psycopg.connect(dsn) as conn:
        row = conn.execute(sql, params).fetchone()
    if row and row[0] and row[1]:
        return ModelMarketQuery(make=str(row[0]), model=str(row[1]))
    if make_guess and model_guess:
        return ModelMarketQuery(make=make_guess, model=model_guess)
    return None

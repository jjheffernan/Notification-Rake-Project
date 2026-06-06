"""UK/DE classified and auction marketplaces — fixture-first, API-ready."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from notification_rake.analysis.auction import analyze_copart_lot
from notification_rake.config import settings
from notification_rake.ingestion.copart.search import CopartLot
from notification_rake.models.listing import VehicleListing

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "eu_marketplaces_sample.json"
)

EU_SOURCE_BASE_URL: dict[str, str] = {
    "ebay_uk": "https://www.ebay.co.uk",
    "gumtree": "https://www.gumtree.com",
    "autoscout24_uk": "https://www.autoscout24.co.uk",
    "copart_uk": "https://www.copart.co.uk",
    "mobile_de": "https://www.mobile.de",
    "autoscout24_de": "https://www.autoscout24.de",
    "ebay_de": "https://www.ebay.de",
    "copart_de": "https://www.copart.de",
}

EU_SOURCE_LABELS: dict[str, str] = {
    "ebay_uk": "eBay UK",
    "gumtree": "Gumtree",
    "autoscout24_uk": "AutoScout24 UK",
    "copart_uk": "Copart UK",
    "mobile_de": "mobile.de",
    "autoscout24_de": "AutoScout24 DE",
    "ebay_de": "eBay DE",
    "copart_de": "Copart DE",
}


@lru_cache(maxsize=1)
def load_fixture_items() -> list[dict[str, Any]]:
    if not _FIXTURE_PATH.is_file():
        return []
    data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return list(data.get("items") or [])


def _fx_to_usd(price: float | None, currency: str | None) -> float | None:
    if price is None:
        return None
    cur = (currency or "USD").upper()
    if cur == "USD":
        return price
    if cur == "GBP" and settings.fx_usd_gbp:
        return round(price / settings.fx_usd_gbp, 2)
    if cur == "EUR" and settings.fx_usd_eur:
        return round(price / settings.fx_usd_eur, 2)
    return price


def _row_to_listing(row: dict[str, Any]) -> VehicleListing:
    source = str(row.get("source") or "")
    currency = row.get("currency")
    price = _fx_to_usd(_to_float(row.get("price")), str(currency) if currency else None)
    image_urls = [str(u) for u in (row.get("image_urls") or []) if u]
    label = EU_SOURCE_LABELS.get(source, source)
    meta: dict[str, Any] = {
        "platform": source,
        "listing_url": row.get("listing_url"),
        "currency": currency,
        "native_price": row.get("price"),
        "city": row.get("city"),
        "badges": [label],
        "fixture": True,
    }
    if source in {"copart_uk", "copart_de"}:
        lot = CopartLot(
            lot_number=str(row.get("source_listing_id") or ""),
            title=str(row.get("title") or ""),
            make=row.get("make"),
            model=row.get("model"),
            year=_to_int(row.get("year")),
            current_bid=price,
            buy_now_price=None,
            auction_status="upcoming",
            auction_date=None,
            primary_damage=row.get("primary_damage"),
            secondary_damage=None,
            loss_type=None,
            run_and_drive=None,
            has_keys=None,
            title_type=row.get("title_type"),
            odometer=_to_int(row.get("mileage")),
            yard_name=row.get("city"),
            yard_state=None,
            country=str(row.get("country") or "GB"),
            latitude=_to_float(row.get("latitude")),
            longitude=_to_float(row.get("longitude")),
            bid_count=None,
            thumbnail_url=image_urls[0] if image_urls else None,
            gallery_urls=image_urls,
            copart_url=str(row.get("listing_url") or ""),
            raw=row,
        )
        analysis = analyze_copart_lot(lot)
        meta["analysis"] = analysis
        meta["badges"] = [label, *(analysis.get("badges") or [])]

    return VehicleListing(
        source=source,
        source_listing_id=str(row.get("source_listing_id") or ""),
        title=row.get("title"),
        make=row.get("make"),
        model=row.get("model"),
        year=_to_int(row.get("year")),
        mileage=_to_int(row.get("mileage")),
        price=price,
        latitude=_to_float(row.get("latitude")),
        longitude=_to_float(row.get("longitude")),
        country=str(row.get("country") or ""),
        image_urls=image_urls,
        metadata=meta,
    )


def fetch_europe_listings(
    *,
    sources: list[str] | None = None,
    query: str = "",
    limit: int = 50,
) -> list[VehicleListing]:
    """Load UK/DE marketplace listings (fixture mode until live APIs are wired)."""
    rows = load_fixture_items()
    if sources:
        allowed = {s.lower() for s in sources}
        rows = [r for r in rows if str(r.get("source") or "").lower() in allowed]
    if query:
        q = query.lower()
        rows = [
            r
            for r in rows
            if q in str(r.get("title") or "").lower()
            or q in str(r.get("make") or "").lower()
            or q in str(r.get("model") or "").lower()
        ]
    return [_row_to_listing(r) for r in rows[:limit]]


def fetch_source_listings(source: str, *, query: str = "", limit: int = 50) -> list[VehicleListing]:
    return fetch_europe_listings(sources=[source], query=query, limit=limit)


def _to_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

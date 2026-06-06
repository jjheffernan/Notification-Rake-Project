"""Yahoo auction hits → VehicleListing."""

from __future__ import annotations

from typing import Any

from notification_rake.analysis.auction import analyze_yahoo_hit
from notification_rake.ingestion.yahoo.search import YahooAuctionHit
from notification_rake.models.listing import VehicleListing
from notification_rake.models.regions import REGION_CENTERS


def yahoo_hit_to_listing(hit: YahooAuctionHit) -> VehicleListing:
    ends_soon = None
    if hit.ends_at:
        from datetime import UTC, datetime

        delta = hit.ends_at - datetime.now(UTC)
        ends_soon = int(delta.total_seconds() // 3600)
    analysis = analyze_yahoo_hit(hit.title, ends_soon_hours=ends_soon)
    price_usd = None
    if hit.current_price_jpy is not None:
        from notification_rake.config import settings

        price_usd = round(hit.current_price_jpy / settings.fx_usd_jpy, 2)
    lon, lat = REGION_CENTERS.get("JP", (139.6503, 35.6762))
    meta: dict[str, Any] = {
        "platform": "yahoo_auctions_jp",
        "auction_id": hit.auction_id,
        "current_price_jpy": hit.current_price_jpy,
        "buyout_price_jpy": hit.buyout_price_jpy,
        "bid_count": hit.bid_count,
        "ends_at": hit.ends_at.isoformat() if hit.ends_at else None,
        "prefecture": hit.prefecture,
        "source_url": hit.source_url,
        "proxy_links": hit.proxy_links,
        "analysis": analysis,
        "badges": analysis.get("badges") or [],
    }
    images = [hit.image_url] if hit.image_url else []
    return VehicleListing(
        source="yahoo_auctions_jp",
        source_listing_id=hit.auction_id,
        title=hit.title,
        price=price_usd,
        latitude=lat,
        longitude=lon,
        country="JP",
        image_urls=images,
        metadata=meta,
    )


def fetch_yahoo_listings(*, query: str = "", max_pages: int = 1) -> list[VehicleListing]:
    from notification_rake.ingestion.yahoo.search import iter_vehicle_search_pages

    pages = iter_vehicle_search_pages(query=query, max_pages=max_pages)
    items: list[VehicleListing] = []
    for page in pages:
        items.extend(yahoo_hit_to_listing(hit) for hit in page.items)
    return items

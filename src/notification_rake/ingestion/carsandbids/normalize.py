"""CarsAndBidsLot → VehicleListing."""

from __future__ import annotations

from typing import Any

from notification_rake.ingestion.carsandbids.search import CarsAndBidsLot, search_auctions
from notification_rake.models.listing import VehicleListing


def lot_to_listing(lot: CarsAndBidsLot) -> VehicleListing:
    price = lot.display_price
    badges = ["Cars & Bids"]
    if lot.auction_status == "sold":
        badges.append("Sold")
    elif lot.auction_status == "live":
        badges.append("Live auction")
    if lot.reserve_met:
        badges.append("Reserve met")

    meta: dict[str, Any] = {
        "platform": "carsandbids",
        "auction_id": lot.auction_id,
        "auction_status": lot.auction_status,
        "ends_at": lot.ends_at.isoformat() if lot.ends_at else None,
        "current_bid": lot.current_bid,
        "sold_price": lot.sold_price,
        "bid_count": lot.bid_count,
        "reserve_met": lot.reserve_met,
        "location": lot.location,
        "listing_url": lot.listing_url,
        "badges": badges,
    }

    return VehicleListing(
        source="carsandbids",
        source_listing_id=lot.auction_id,
        title=lot.title,
        description=lot.location,
        make=lot.make,
        model=lot.model,
        year=lot.year,
        mileage=lot.mileage,
        price=price,
        latitude=lot.latitude,
        longitude=lot.longitude,
        country=lot.country,
        image_urls=lot.image_urls,
        metadata=meta,
    )


def fetch_listings(
    *, query: str = "", mode: str = "active", limit: int = 50
) -> list[VehicleListing]:
    result = search_auctions(query=query, mode=mode, limit=limit)
    return [lot_to_listing(lot) for lot in result.items]

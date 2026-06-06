"""CopartLot → VehicleListing + auction metadata."""

from __future__ import annotations

from typing import Any

from notification_rake.analysis.auction import analyze_copart_lot
from notification_rake.ingestion.copart.search import CopartLot, search_lots
from notification_rake.models.listing import VehicleListing


def copart_lot_to_listing(lot: CopartLot) -> VehicleListing:
    analysis = analyze_copart_lot(lot)
    price = lot.current_bid if lot.current_bid is not None else lot.buy_now_price
    meta: dict[str, Any] = {
        "platform": "copart",
        "lot_number": lot.lot_number,
        "auction_status": lot.auction_status,
        "auction_date": lot.auction_date.isoformat() if lot.auction_date else None,
        "primary_damage": lot.primary_damage,
        "secondary_damage": lot.secondary_damage,
        "loss_type": lot.loss_type,
        "run_and_drive": lot.run_and_drive,
        "has_keys": lot.has_keys,
        "title_type": lot.title_type,
        "bid_count": lot.bid_count,
        "yard_name": lot.yard_name,
        "yard_state": lot.yard_state,
        "copart_url": lot.copart_url,
        "analysis": analysis,
        "badges": analysis.get("badges") or [],
    }
    desc_parts = [
        p for p in [lot.primary_damage, lot.title_type, lot.yard_name, lot.yard_state] if p
    ]
    return VehicleListing(
        source="copart",
        source_listing_id=lot.lot_number,
        title=lot.title,
        description=" · ".join(desc_parts),
        make=lot.make,
        model=lot.model,
        year=lot.year,
        mileage=lot.odometer,
        price=price,
        latitude=lot.latitude,
        longitude=lot.longitude,
        country=lot.country,
        image_urls=lot.image_urls,
        metadata=meta,
    )


def fetch_listings(
    *, query: str = "", state: str | None = None, limit: int = 50
) -> list[VehicleListing]:
    result = search_lots(query=query, state=state, limit=limit)
    return [copart_lot_to_listing(lot) for lot in result.items]

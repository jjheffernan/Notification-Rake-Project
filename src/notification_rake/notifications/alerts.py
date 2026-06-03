"""Notify on newly discovered listings."""

from __future__ import annotations

from notification_rake.integrations.gotify import send_alert
from notification_rake.models.listing import VehicleListing


def format_listing_message(listing: VehicleListing) -> str:
    parts = [listing.title or "Untitled listing"]
    if listing.price is not None:
        parts.append(f"${listing.price:,.0f}")
    if listing.year:
        parts.append(str(listing.year))
    if listing.make and listing.model:
        parts.append(f"{listing.make} {listing.model}")
    return " · ".join(parts)


def notify_new_listings(listings: list[VehicleListing]) -> int:
    """Push Gotify alerts for new listings; returns count sent."""
    sent = 0
    for item in listings:
        send_alert(
            title="New vehicle listing",
            message=format_listing_message(item),
            priority=5,
        )
        sent += 1
    return sent

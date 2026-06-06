"""Copart auction ingestion — search, detail, normalize."""

from notification_rake.ingestion.copart.client import CopartClient, load_sample_lots
from notification_rake.ingestion.copart.detail import fetch_lot_detail
from notification_rake.ingestion.copart.normalize import copart_lot_to_listing, fetch_listings
from notification_rake.ingestion.copart.search import CopartLot, search_lots

__all__ = [
    "CopartClient",
    "CopartLot",
    "copart_lot_to_listing",
    "fetch_listings",
    "fetch_lot_detail",
    "load_sample_lots",
    "search_lots",
]

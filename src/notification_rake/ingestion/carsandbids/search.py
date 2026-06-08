"""Cars & Bids auction search — fixture or provider API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from notification_rake.ingestion.carsandbids.client import CarsAndBidsClient, load_sample_auctions


@dataclass(frozen=True)
class CarsAndBidsLot:
    auction_id: str
    title: str
    make: str | None
    model: str | None
    year: int | None
    mileage: int | None
    current_bid: float | None
    sold_price: float | None
    auction_status: str | None
    ends_at: datetime | None
    bid_count: int | None
    reserve_met: bool | None
    location: str | None
    country: str
    latitude: float | None
    longitude: float | None
    image_urls: list[str]
    listing_url: str
    raw: dict[str, Any]

    @property
    def display_price(self) -> float | None:
        if self.sold_price is not None:
            return self.sold_price
        return self.current_bid


@dataclass(frozen=True)
class CarsAndBidsSearchResult:
    total: int
    items: list[CarsAndBidsLot]
    raw: dict[str, Any]


def search_auctions(
    *,
    query: str = "",
    mode: str = "active",
    limit: int = 50,
    client: CarsAndBidsClient | None = None,
) -> CarsAndBidsSearchResult:
    client = client or CarsAndBidsClient.from_settings()
    if client.use_fixture():
        raw = load_sample_auctions()
    else:
        params: dict[str, Any] = {"q": query, "mode": mode, "limit": limit}
        raw = client.get_json("auctions/search", params)

    items = parse_auction_rows(raw.get("items") or raw.get("results") or [])
    if query:
        q = query.lower()
        items = [
            lot
            for lot in items
            if q in (lot.title or "").lower()
            or q in (lot.make or "").lower()
            or q in (lot.model or "").lower()
        ]
    if mode == "active":
        items = [lot for lot in items if lot.auction_status in {"live", "active", None}]
    elif mode == "past":
        items = [lot for lot in items if lot.auction_status in {"sold", "ended"}]
    total = int(raw.get("total") or len(items))
    return CarsAndBidsSearchResult(total=total, items=items[:limit], raw=raw)


def parse_auction_rows(rows: list[dict[str, Any]]) -> list[CarsAndBidsLot]:
    return [_parse_auction(row) for row in rows if row]


def _parse_auction(row: dict[str, Any]) -> CarsAndBidsLot:
    auction_id = str(row.get("auction_id") or row.get("id") or "")
    gallery = row.get("image_urls") or row.get("photos") or []
    if isinstance(gallery, str):
        gallery = [gallery]
    url = row.get("listing_url") or row.get("url") or f"https://carsandbids.com/auctions/{auction_id}"
    return CarsAndBidsLot(
        auction_id=auction_id,
        title=str(row.get("title") or ""),
        make=row.get("make"),
        model=row.get("model"),
        year=_to_int(row.get("year")),
        mileage=_to_int(row.get("mileage")),
        current_bid=_to_float(row.get("current_bid") or row.get("currentBid")),
        sold_price=_to_float(row.get("sold_price") or row.get("soldPrice")),
        auction_status=row.get("auction_status") or row.get("status"),
        ends_at=_parse_dt(row.get("ends_at") or row.get("endsAt")),
        bid_count=_to_int(row.get("bid_count") or row.get("bidCount")),
        reserve_met=_to_bool(row.get("reserve_met") or row.get("reserveMet")),
        location=row.get("location"),
        country=str(row.get("country") or "US"),
        latitude=_to_float(row.get("latitude")),
        longitude=_to_float(row.get("longitude")),
        image_urls=[str(u) for u in gallery if u],
        listing_url=str(url),
        raw=row,
    )


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes", "y"}

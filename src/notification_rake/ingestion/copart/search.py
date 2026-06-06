"""Copart lot search — fixture or provider API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from notification_rake.ingestion.copart.client import CopartClient, load_sample_lots


@dataclass(frozen=True)
class CopartLot:
    lot_number: str
    title: str
    make: str | None
    model: str | None
    year: int | None
    current_bid: float | None
    buy_now_price: float | None
    auction_status: str | None
    auction_date: datetime | None
    primary_damage: str | None
    secondary_damage: str | None
    loss_type: str | None
    run_and_drive: bool | None
    has_keys: bool | None
    title_type: str | None
    odometer: int | None
    yard_name: str | None
    yard_state: str | None
    country: str
    latitude: float | None
    longitude: float | None
    bid_count: int | None
    thumbnail_url: str | None
    gallery_urls: list[str]
    copart_url: str
    raw: dict[str, Any]

    @property
    def image_urls(self) -> list[str]:
        if self.gallery_urls:
            return self.gallery_urls
        return [self.thumbnail_url] if self.thumbnail_url else []


@dataclass(frozen=True)
class CopartSearchResult:
    total: int
    items: list[CopartLot]
    raw: dict[str, Any]


def search_lots(
    *,
    query: str = "",
    state: str | None = None,
    limit: int = 50,
    client: CopartClient | None = None,
) -> CopartSearchResult:
    client = client or CopartClient.from_settings()
    if client.use_fixture():
        raw = load_sample_lots()
    else:
        params: dict[str, Any] = {"q": query, "limit": limit}
        if state:
            params["state"] = state
        raw = client.get_json("lots/search", params)

    items = parse_lot_rows(raw.get("items") or raw.get("results") or [])
    if query:
        q = query.lower()
        items = [
            lot
            for lot in items
            if q in (lot.title or "").lower()
            or q in (lot.make or "").lower()
            or q in (lot.model or "").lower()
        ]
    if state:
        items = [lot for lot in items if (lot.yard_state or "").upper() == state.upper()]
    total = int(raw.get("total") or len(items))
    return CopartSearchResult(total=total, items=items[:limit], raw=raw)


def parse_lot_rows(rows: list[dict[str, Any]]) -> list[CopartLot]:
    return [_parse_lot(row) for row in rows if row]


def _parse_lot(row: dict[str, Any]) -> CopartLot:
    lot_number = str(row.get("lot_number") or row.get("lotNumber") or "")
    gallery = row.get("gallery_urls") or row.get("galleryUrls") or []
    if isinstance(gallery, str):
        gallery = [gallery]
    thumb = row.get("thumbnail_url") or row.get("thumbnailUrl")
    ends = _parse_dt(row.get("auction_date") or row.get("auctionDate"))
    url = row.get("copart_url") or row.get("copartUrl") or f"https://www.copart.com/lot/{lot_number}"
    return CopartLot(
        lot_number=lot_number,
        title=str(row.get("title") or ""),
        make=row.get("make"),
        model=row.get("model"),
        year=_to_int(row.get("year")),
        current_bid=_to_float(row.get("current_bid") or row.get("currentBid")),
        buy_now_price=_to_float(row.get("buy_now_price") or row.get("buyNowPrice")),
        auction_status=row.get("auction_status") or row.get("auctionStatus"),
        auction_date=ends,
        primary_damage=row.get("primary_damage") or row.get("primaryDamage"),
        secondary_damage=row.get("secondary_damage") or row.get("secondaryDamage"),
        loss_type=row.get("loss_type") or row.get("lossType"),
        run_and_drive=_to_bool(row.get("run_and_drive") or row.get("runAndDrive")),
        has_keys=_to_bool(row.get("has_keys") or row.get("hasKeys")),
        title_type=row.get("title_type") or row.get("titleType"),
        odometer=_to_int(row.get("odometer")),
        yard_name=row.get("yard_name") or row.get("yardName"),
        yard_state=row.get("yard_state") or row.get("yardState"),
        country=str(row.get("country") or "US"),
        latitude=_to_float(row.get("latitude")),
        longitude=_to_float(row.get("longitude")),
        bid_count=_to_int(row.get("bid_count") or row.get("bidCount")),
        thumbnail_url=thumb,
        gallery_urls=[str(u) for u in gallery if u],
        copart_url=str(url),
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

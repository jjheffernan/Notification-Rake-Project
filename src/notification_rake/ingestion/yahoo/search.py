"""Yahoo Auctions search — phase 0 discovery + field mapping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from notification_rake.config import settings
from notification_rake.ingestion.yahoo.categories import (
    PROXY_DEEP_LINKS,
    YAHOO_ITEM_URL,
)
from notification_rake.ingestion.yahoo.client import YahooClient

SortKey = Literal["cbids", "end", "bids", "img", "bidorbuy"]
OrderKey = Literal["a", "d"]


@dataclass(frozen=True)
class YahooAuctionHit:
    auction_id: str
    title: str
    current_price_jpy: float | None
    buyout_price_jpy: float | None
    bid_count: int | None
    ends_at: datetime | None
    image_url: str | None
    category_id: str | None
    prefecture: str | None
    source_url: str
    proxy_links: dict[str, str]

    @property
    def field_map(self) -> dict[str, Any]:
        """Normalized keys for notebook / ingest mapping."""
        return {
            "auction_id": self.auction_id,
            "title": self.title,
            "current_price_jpy": self.current_price_jpy,
            "buyout_price_jpy": self.buyout_price_jpy,
            "bid_count": self.bid_count,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "image_url": self.image_url,
            "category_id": self.category_id,
            "prefecture": self.prefecture,
            "source_url": self.source_url,
            "proxy_links": self.proxy_links,
        }


@dataclass(frozen=True)
class YahooSearchResult:
    query: str
    category: int
    page: int
    total_available: int
    total_returned: int
    items: list[YahooAuctionHit]
    raw: dict[str, Any]

    def sample_fields(self) -> list[dict[str, Any]]:
        return [item.field_map for item in self.items[:5]]


def search_vehicle_auctions(
    *,
    query: str = "",
    category: int | None = None,
    page: int = 1,
    results: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    loc_code: int | None = None,
    sort: SortKey = "end",
    order: OrderKey = "a",
    client: YahooClient | None = None,
) -> YahooSearchResult:
    """Search Yahoo Auctions in the vehicle category (default 26360)."""
    client = client or YahooClient.from_settings()
    category = category if category is not None else settings.yahoo_vehicle_auccat
    page_size = results or settings.yahoo_ingest_page_size

    params: dict[str, Any] = {
        "query": query,
        "category": category,
        "page": page,
        "results": min(max(page_size, 1), 50),
        "sort": sort,
        "order": order,
    }
    if min_price is not None:
        params["aucminprice"] = min_price
    if max_price is not None:
        params["aucmaxprice"] = max_price
    if loc_code is not None:
        params["loc_code"] = loc_code

    raw = client.get_json("search", params)
    items = parse_search_items(raw)
    totals = _result_totals(raw)
    return YahooSearchResult(
        query=query,
        category=category,
        page=page,
        total_available=totals[0],
        total_returned=totals[1],
        items=items,
        raw=raw,
    )


def iter_vehicle_search_pages(
    *,
    query: str = "",
    category: int | None = None,
    max_pages: int = 1,
    client: YahooClient | None = None,
    **kwargs: Any,
) -> list[YahooSearchResult]:
    """Fetch up to `max_pages` of search results (respects client daily budget)."""
    client = client or YahooClient.from_settings()
    pages: list[YahooSearchResult] = []
    for page in range(1, max_pages + 1):
        result = search_vehicle_auctions(
            query=query,
            category=category,
            page=page,
            client=client,
            **kwargs,
        )
        pages.append(result)
        if not result.items:
            break
        page_size = len(result.items)
        if result.total_available and page * page_size >= result.total_available:
            break
    return pages


def parse_search_items(payload: dict[str, Any]) -> list[YahooAuctionHit]:
    items_raw = _extract_items(payload)
    return [_parse_item(row) for row in items_raw if row]


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result_set = payload.get("ResultSet") or payload.get("resultset") or {}
    result = result_set.get("Result") or result_set.get("result") or {}
    items = result.get("Item") or result.get("item") or []
    if isinstance(items, dict):
        return [items]
    if isinstance(items, list):
        return [i for i in items if isinstance(i, dict)]
    return []


def _result_totals(payload: dict[str, Any]) -> tuple[int, int]:
    result_set = payload.get("ResultSet") or payload.get("resultset") or {}
    available = _to_int(
        result_set.get("totalResultsAvailable") or result_set.get("totalresultsavailable")
    )
    returned = _to_int(
        result_set.get("totalResultsReturned") or result_set.get("totalresultsreturned")
    )
    return available, returned


def _parse_item(row: dict[str, Any]) -> YahooAuctionHit:
    auction_id = str(row.get("AuctionID") or row.get("auctionID") or row.get("AuctionId") or "")
    title = str(row.get("Title") or row.get("title") or "")
    current = _to_float(row.get("CurrentPrice") or row.get("currentPrice"))
    buyout = _to_float(row.get("BidOrBuy") or row.get("BuyItNowPrice") or row.get("bidOrBuy"))
    bids = _to_int(row.get("Bids") or row.get("bids"))
    ends_at = _parse_end_time(row.get("EndTime") or row.get("endTime"))
    image = _first_image(row.get("Image") or row.get("image"))
    category_id = str(row.get("CategoryID") or row.get("CategoryId") or row.get("categoryId") or "")
    prefecture = _location_name(row.get("Location") or row.get("location"))

    proxy_links = {
        name: template.format(auction_id=auction_id)
        for name, template in PROXY_DEEP_LINKS.items()
    }
    return YahooAuctionHit(
        auction_id=auction_id,
        title=title,
        current_price_jpy=current,
        buyout_price_jpy=buyout,
        bid_count=bids,
        ends_at=ends_at,
        image_url=image,
        category_id=category_id or None,
        prefecture=prefecture,
        source_url=YAHOO_ITEM_URL.format(auction_id=auction_id),
        proxy_links=proxy_links,
    )


def _first_image(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        for key in ("Medium", "medium", "Small", "small", "Url", "url"):
            if value.get(key):
                return str(value[key])
    if isinstance(value, list) and value:
        return _first_image(value[0])
    return None


def _location_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        for key in ("Prefecture", "prefecture", "City", "city", "Name", "name"):
            if value.get(key):
                return str(value[key])
    return None


def _parse_end_time(value: Any) -> datetime | None:
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


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

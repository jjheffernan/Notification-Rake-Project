"""Account connectors — fetch listings from user-linked marketplace accounts."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from notification_rake.ingestion.carsandbids.normalize import fetch_listings as fetch_carsandbids
from notification_rake.ingestion.copart.normalize import fetch_listings as fetch_copart
from notification_rake.ingestion.craigslist import fetch_listings as fetch_craigslist
from notification_rake.ingestion.europe.normalize import fetch_source_listings
from notification_rake.ingestion.yahoo.normalize import fetch_yahoo_listings
from notification_rake.models.listing import VehicleListing

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = frozenset(
    {
        "craigslist",
        "yahoo_auctions_jp",
        "buyee",
        "ebay",
        "ebay_uk",
        "ebay_de",
        "copart",
        "copart_uk",
        "copart_de",
        "gumtree",
        "autoscout24_uk",
        "autoscout24_de",
        "mobile_de",
        "carsandbids",
    }
)


@dataclass(frozen=True)
class ConnectorConfig:
    provider: str
    label: str
    config: dict[str, Any]


class AccountConnector(Protocol):
    provider: str

    def fetch(self, cfg: ConnectorConfig) -> list[VehicleListing]: ...


def fetch_from_connector(cfg: ConnectorConfig) -> list[VehicleListing]:
    provider = cfg.provider.lower()
    if provider == "craigslist":
        return _fetch_craigslist(cfg)
    if provider == "yahoo_auctions_jp":
        return _fetch_yahoo(cfg)
    if provider == "copart":
        return _fetch_copart(cfg)
    if provider == "buyee":
        return _fetch_buyee(cfg)
    if provider == "ebay":
        return _fetch_ebay(cfg)
    if provider in {"ebay_uk", "ebay_de"}:
        return _fetch_ebay_marketplace(cfg, provider)
    if provider in {"gumtree", "autoscout24_uk", "autoscout24_de", "mobile_de"}:
        return _fetch_europe_source(cfg, provider)
    if provider in {"copart_uk", "copart_de"}:
        return _fetch_europe_copart(cfg, provider)
    if provider == "carsandbids":
        return _fetch_carsandbids(cfg)
    raise ValueError(f"unsupported provider: {provider}")


def fetch_all_connected(configs: list[ConnectorConfig]) -> list[VehicleListing]:
    items: list[VehicleListing] = []
    for cfg in configs:
        try:
            batch = fetch_from_connector(cfg)
            for item in batch:
                meta = {**item.metadata, "connected_account": cfg.label or cfg.provider}
                items.append(item.model_copy(update={"metadata": meta}))
        except Exception as exc:
            logger.warning("connector %s failed: %s", cfg.provider, exc)
    return items


def _fetch_craigslist(cfg: ConnectorConfig) -> list[VehicleListing]:
    rss_url = cfg.config.get("rss_url") or cfg.config.get("search_rss")
    if not rss_url:
        raise ValueError("craigslist connector requires rss_url")
    return fetch_craigslist(rss_url)


def _fetch_yahoo(cfg: ConnectorConfig) -> list[VehicleListing]:
    query = cfg.config.get("query", "")
    pages = int(cfg.config.get("max_pages", 1))
    return fetch_yahoo_listings(query=query, max_pages=pages)


def _fetch_copart(cfg: ConnectorConfig) -> list[VehicleListing]:
    return fetch_copart(
        query=cfg.config.get("query", ""),
        state=cfg.config.get("state"),
        limit=int(cfg.config.get("limit", 50)),
    )


def _fetch_buyee(cfg: ConnectorConfig) -> list[VehicleListing]:
    query = cfg.config.get("watchlist_query") or cfg.config.get("query", "")
    items = fetch_yahoo_listings(query=query, max_pages=1)
    for item in items:
        if cfg.config.get("member_id"):
            item.metadata["buyee_member"] = cfg.config["member_id"]
    return items


def _fetch_ebay(cfg: ConnectorConfig) -> list[VehicleListing]:
    api_key = cfg.config.get("api_key") or cfg.config.get("oauth_token")
    query = cfg.config.get("query", "vehicle")
    if api_key:
        return _fetch_ebay_api(api_key, query, cfg.config)
    return _fetch_ebay_fixture(query)


def _fetch_ebay_marketplace(cfg: ConnectorConfig, provider: str) -> list[VehicleListing]:
    country = "GB" if provider == "ebay_uk" else "DE"
    api_key = cfg.config.get("api_key") or cfg.config.get("oauth_token")
    query = cfg.config.get("query", "vehicle")
    if api_key:
        marketplace = cfg.config.get("marketplace") or ("EBAY_GB" if country == "GB" else "EBAY_DE")
        config = {**cfg.config, "marketplace": marketplace}
        items = _fetch_ebay_api(api_key, query, config)
        return [
            item.model_copy(
                update={
                    "source": provider,
                    "country": country,
                    "metadata": {**item.metadata, "platform": provider, "marketplace": marketplace},
                }
            )
            for item in items
        ]
    return fetch_source_listings(provider, query=query, limit=int(cfg.config.get("limit", 20)))


def _fetch_europe_source(cfg: ConnectorConfig, provider: str) -> list[VehicleListing]:
    query = cfg.config.get("query", "")
    limit = int(cfg.config.get("limit", 50))
    return fetch_source_listings(provider, query=query, limit=limit)


def _fetch_europe_copart(cfg: ConnectorConfig, provider: str) -> list[VehicleListing]:
    query = cfg.config.get("query", "")
    limit = int(cfg.config.get("limit", 50))
    return fetch_source_listings(provider, query=query, limit=limit)


def _fetch_carsandbids(cfg: ConnectorConfig) -> list[VehicleListing]:
    return fetch_carsandbids(
        query=cfg.config.get("query", ""),
        mode=str(cfg.config.get("mode", "active")),
        limit=int(cfg.config.get("limit", 50)),
    )


def _fetch_ebay_api(api_key: str, query: str, config: dict[str, Any]) -> list[VehicleListing]:
    url = config.get("api_base", "https://api.ebay.com/buy/browse/v1/item_summary/search")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if config.get("marketplace"):
        headers["X-EBAY-C-MARKETPLACE-ID"] = str(config["marketplace"])
    params = {"q": query, "limit": str(config.get("limit", 20))}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    items: list[VehicleListing] = []
    for row in data.get("itemSummaries") or []:
        item_id = str(row.get("itemId") or "")
        price_val = row.get("price") or {}
        price = float(price_val.get("value")) if price_val.get("value") else None
        image = (row.get("image") or {}).get("imageUrl")
        items.append(
            VehicleListing(
                source="ebay",
                source_listing_id=item_id,
                title=row.get("title"),
                price=price,
                country="US",
                image_urls=[image] if image else [],
                metadata={
                    "platform": "ebay",
                    "item_web_url": row.get("itemWebUrl"),
                    "badges": ["eBay"],
                },
            )
        )
    return items


def _fetch_ebay_fixture(query: str) -> list[VehicleListing]:
    return [
        VehicleListing(
            source="ebay",
            source_listing_id="ebay-sample-1",
            title=f"Sample eBay listing — {query or 'vehicle'}",
            price=12500.0,
            make="Toyota",
            model="Supra",
            year=1994,
            country="US",
            image_urls=["https://i.ebayimg.com/images/g/sample1/s-l500.jpg"],
            metadata={"platform": "ebay", "badges": ["eBay", "Connected account"], "fixture": True},
        )
    ]

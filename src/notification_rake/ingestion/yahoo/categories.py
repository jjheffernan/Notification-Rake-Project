"""Yahoo Auctions category IDs and proxy link templates."""

from __future__ import annotations

# 自動車、オートバイ
AUCCAT_AUTO_MOTO = 26318

# 中古車・新車 (used/new car bodies) — primary vehicle ingest target
AUCCAT_USED_NEW_CARS = 26360

DEFAULT_VEHICLE_AUCCAT = AUCCAT_USED_NEW_CARS

# Yahoo prefecture loc_code 1–48 (1=Hokkaido … 48=overseas). Sample for phase 0 filters.
PREFECTURE_CODES: dict[int, str] = {
    1: "Hokkaido",
    13: "Tokyo",
    14: "Kanagawa",
    23: "Aichi",
    27: "Osaka",
}

PROXY_DEEP_LINKS: dict[str, str] = {
    "buyee": "https://buyee.jp/item/yahoo/auction/{auction_id}",
    "neokyo": "https://neokyo.com/en/yahoo-auction/{auction_id}",
    "fromjapan": "https://www.fromjapan.co.jp/en/auction/item/{auction_id}",
}

YAHOO_ITEM_URL = "https://page.auctions.yahoo.co.jp/jp/auction/{auction_id}"

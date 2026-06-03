"""Craigslist ingestion — MVP Phase 1 source."""

from __future__ import annotations

import re
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path

import httpx

from notification_rake.models.listing import VehicleListing

PRICE_RE = re.compile(r"\$[\d,]+")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "craigslist_sample.rss"


def fetch_search_rss(search_url: str, *, user_agent: str = DEFAULT_USER_AGENT) -> str:
    """GET Craigslist search RSS with browser User-Agent."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }
    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(search_url)
        resp.raise_for_status()
        return resp.text


def load_sample_rss() -> str:
    """Offline dev fixture when Craigslist blocks RSS (403)."""
    try:
        path = files("notification_rake.fixtures").joinpath("craigslist_sample.rss")
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError, OSError):
        return _FIXTURE_PATH.read_text(encoding="utf-8")


def fetch_listings(
    search_url: str,
    *,
    use_sample_on_403: bool = True,
) -> list[VehicleListing]:
    """Fetch live RSS; on 403 use bundled sample (Craigslist blocks RSS in Docker)."""
    try:
        xml = fetch_search_rss(search_url)
    except httpx.HTTPStatusError as exc:
        if use_sample_on_403 and exc.response.status_code == 403:
            xml = load_sample_rss()
        else:
            raise
    return list(parse_rss_items(xml))


def parse_rss_items(rss_xml: str, source: str = "craigslist") -> Iterator[VehicleListing]:
    """Split RSS by `<item>`, yield VehicleListing per entry with link."""
    for block in rss_xml.split("<item>")[1:]:
        title = _tag(block, "title")
        link = _tag(block, "link")
        desc = _tag(block, "description")
        if not link:
            continue
        listing_id = link.rstrip("/").split("/")[-1].removesuffix(".html")
        yield VehicleListing(
            source=source,
            source_listing_id=listing_id,
            title=title,
            description=desc,
            price=_parse_price(title or desc or ""),
            year=_parse_year(title or ""),
        )


def _tag(block: str, name: str) -> str | None:
    open_tag = f"<{name}>"
    close_tag = f"</{name}>"
    if open_tag not in block:
        return None
    return block.split(open_tag, 1)[1].split(close_tag, 1)[0].strip()


def _parse_price(text: str) -> float | None:
    match = PRICE_RE.search(text)
    if not match:
        return None
    return float(match.group().replace("$", "").replace(",", ""))


def _parse_year(text: str) -> int | None:
    match = YEAR_RE.search(text)
    return int(match.group()) if match else None

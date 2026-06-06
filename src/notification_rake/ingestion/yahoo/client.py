"""HTTP client for Yahoo Auctions Web API v2."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

import httpx

from notification_rake.config import settings

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; notification-rake/0.1.0; +https://github.com/)"
)
_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures"
_FIXTURE_PATH = _FIXTURE_DIR / "yahoo_vehicle_search_sample.json"


@dataclass
class YahooClientStats:
    requests_today: int = 0
    daily_budget: int = 0
    last_request_at: datetime | None = None


@dataclass
class YahooClient:
    """Thin wrapper around auctions.yahooapis.jp with daily request budget."""

    app_id: str = ""
    api_base: str = ""
    daily_budget: int = 45_000
    timeout: float = 30.0
    user_agent: str = DEFAULT_USER_AGENT
    _stats: YahooClientStats = field(default_factory=YahooClientStats)
    _day: str = ""

    @classmethod
    def from_settings(cls) -> YahooClient:
        return cls(
            app_id=settings.yahoo_app_id,
            api_base=settings.yahoo_auction_api_base.rstrip("/"),
            daily_budget=settings.yahoo_requests_per_day,
        )

    def get_json(
        self,
        resource: str,
        params: dict[str, Any],
        *,
        use_sample_on_missing_appid: bool = True,
    ) -> dict[str, Any]:
        """GET `{api_base}/{resource}` with `output=json` and parse JSON body."""
        if not self.app_id:
            if use_sample_on_missing_appid and resource.endswith("search"):
                logger.warning("YAHOO_APP_ID unset — using bundled search fixture")
                return load_sample_search()
            raise ValueError("YAHOO_APP_ID is required for live Yahoo Auction API calls")

        self._check_budget()
        query = {"appid": self.app_id, "output": "json", **params}
        url = f"{self.api_base}/{resource.lstrip('/')}"

        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as http:
            resp = http.get(url, params=query)
            resp.raise_for_status()
            payload = _parse_json_body(resp.text)

        self._record_request()
        return payload

    def _check_budget(self) -> None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if today != self._day:
            self._day = today
            self._stats.requests_today = 0
        if self._stats.requests_today >= self.daily_budget:
            raise RuntimeError(
                f"Yahoo API daily budget exhausted ({self.daily_budget} requests)"
            )

    def _record_request(self) -> None:
        self._stats.requests_today += 1
        self._stats.last_request_at = datetime.now(UTC)

    @property
    def stats(self) -> YahooClientStats:
        return self._stats


def load_sample_search() -> dict[str, Any]:
    """Offline fixture when appid missing or API unreachable."""
    try:
        path = files("notification_rake.fixtures").joinpath("yahoo_vehicle_search_sample.json")
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, TypeError, OSError, json.JSONDecodeError):
        return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _parse_json_body(text: str) -> dict[str, Any]:
    """Yahoo may return raw JSON or JSONP (`callback({...})`)."""
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        data = json.loads(stripped)
    elif "(" in stripped and stripped.endswith(")"):
        start = stripped.index("(") + 1
        data = json.loads(stripped[start:-1])
    else:
        raise ValueError("Unexpected Yahoo API response format")
    if not isinstance(data, dict):
        raise ValueError("Yahoo API response must be a JSON object")
    return data

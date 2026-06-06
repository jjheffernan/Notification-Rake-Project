"""Copart HTTP client — provider API or fixture fallback."""

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

_FIXTURE_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "copart_sample.json"


@dataclass
class CopartClientStats:
    requests_today: int = 0
    daily_budget: int = 0


@dataclass
class CopartClient:
    api_base: str = ""
    api_key: str = ""
    api_mode: str = "auto"
    daily_budget: int = 5000
    timeout: float = 30.0
    _stats: CopartClientStats = field(default_factory=CopartClientStats)
    _day: str = ""

    @classmethod
    def from_settings(cls) -> CopartClient:
        return cls(
            api_base=settings.copart_api_base.rstrip("/"),
            api_key=settings.copart_api_key,
            api_mode=settings.copart_api_mode,
            daily_budget=settings.copart_requests_per_day,
        )

    def use_fixture(self) -> bool:
        if self.api_mode == "fixture":
            return True
        if self.api_mode == "auto" and not self.api_key:
            return True
        return False

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.use_fixture():
            logger.warning("Copart fixture mode — using bundled sample lots")
            return load_sample_lots()

        self._check_budget()
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        url = f"{self.api_base}/{path.lstrip('/')}"
        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as http:
            resp = http.get(url, params=params or {})
            resp.raise_for_status()
            data = resp.json()
        self._record_request()
        if not isinstance(data, dict):
            raise ValueError("Copart API response must be a JSON object")
        return data

    def _check_budget(self) -> None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if today != self._day:
            self._day = today
            self._stats.requests_today = 0
        if self._stats.requests_today >= self.daily_budget:
            raise RuntimeError(f"Copart API daily budget exhausted ({self.daily_budget})")

    def _record_request(self) -> None:
        self._stats.requests_today += 1


def load_sample_lots() -> dict[str, Any]:
    try:
        path = files("notification_rake.fixtures").joinpath("copart_sample.json")
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, TypeError, OSError, json.JSONDecodeError):
        return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))

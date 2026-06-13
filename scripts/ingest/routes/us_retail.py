"""Run US retail ingest route (Craigslist)."""

from __future__ import annotations

from ingest._common import run_route_script

ALIASES = ("ingest_us_retail",)


def run() -> int:
    return run_route_script("us-retail")

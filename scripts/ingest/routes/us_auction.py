"""Run US auction ingest route (Copart + Cars & Bids)."""

from __future__ import annotations

from ingest._common import run_route_script

ALIASES = ("ingest_us_auction",)


def run() -> int:
    return run_route_script("us-auction")

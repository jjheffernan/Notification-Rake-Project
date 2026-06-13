"""Run Japan ingest route (Yahoo Auctions JP)."""

from __future__ import annotations

from ingest._common import run_route_script

ALIASES = ("ingest_jp",)


def run() -> int:
    return run_route_script("jp")

"""Run UK ingest route."""

from __future__ import annotations

from ingest._common import run_route_script

ALIASES = ("ingest_uk",)


def run() -> int:
    return run_route_script("uk")

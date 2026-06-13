"""Run all bulk ingest routes."""

from __future__ import annotations

from ingest._common import run_all_routes_script

ALIASES = ("ingest_all",)


def run() -> int:
    return run_all_routes_script()

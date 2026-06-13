"""Yahoo Auctions JP ingest."""

from __future__ import annotations

from ingest._common import run_source_script
from notification_rake.workflow.multi_source import ingest_yahoo

ALIASES = ("ingest_yahoo",)


def run() -> int:
    return run_source_script(ingest_yahoo, label="yahoo")

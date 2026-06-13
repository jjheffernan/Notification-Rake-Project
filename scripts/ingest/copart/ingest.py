"""Copart auction ingest."""

from __future__ import annotations

from ingest._common import run_source_script
from notification_rake.workflow.multi_source import ingest_copart

ALIASES = ("copart", "ingest_copart")


def run() -> int:
    return run_source_script(ingest_copart, label="copart")

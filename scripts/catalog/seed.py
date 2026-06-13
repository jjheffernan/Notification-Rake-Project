"""Seed canonical vehicle makes/models."""

from __future__ import annotations

from notification_rake.config import settings
from notification_rake.storage import seed_catalog

ALIASES = ("seed",)


def run() -> int:
    count = seed_catalog(settings.database_url)
    print(f"seed: {count} vehicle_model rows in catalog")
    print(f"database: {settings.database_url}")
    return 0

"""Normalize listing titles against catalog."""

from __future__ import annotations

from notification_rake.config import settings
from notification_rake.storage import seed_catalog
from notification_rake.transform import load_catalog
from notification_rake.workflow import ingest, normalize

ALIASES = ("normalize",)


def run() -> int:
    seed_catalog(settings.database_url)
    raw = ingest()
    out = normalize(raw)
    matched = sum(1 for n in out if n.make and n.model)
    catalog = load_catalog(settings.database_url)
    source = "database" if catalog else "empty"
    print(f"normalize: {matched}/{len(out)} matched canonical make/model")
    for item in out:
        print(f"  - {item.title!r} -> {item.make}/{item.model}")
    print(f"catalog source: {source} ({len(catalog)} models)")
    return 0

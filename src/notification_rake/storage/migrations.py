"""Apply SQL layer migrations on existing databases."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION_FILES = (
    _REPO_ROOT / "db" / "init" / "003_schemas.sql",
    _REPO_ROOT / "db" / "init" / "005_saved_search.sql",
    _REPO_ROOT / "db" / "init" / "006_country.sql",
    _REPO_ROOT / "db" / "init" / "007_copart_accounts.sql",
    _REPO_ROOT / "db" / "init" / "008_eu_marketplaces.sql",
    _REPO_ROOT / "db" / "init" / "009_carsandbids.sql",
    _REPO_ROOT / "db" / "init" / "010_scheduled_search.sql",
)


def apply_layer_schema(dsn: str) -> None:
    """Apply schema migration SQL files."""
    import psycopg

    with psycopg.connect(dsn) as conn:
        for path in _MIGRATION_FILES:
            if path.is_file():
                conn.execute(path.read_text(encoding="utf-8"))
        conn.commit()

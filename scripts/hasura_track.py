"""Container script: track Postgres tables in Hasura for GraphQL."""

from __future__ import annotations

from notification_rake.config import settings
from notification_rake.integrations import track_tables


def run() -> int:
    tracked = track_tables()
    print(f"hasura: tracked {len(tracked)} tables at {settings.hasura_url}")
    for name in tracked:
        print(f"  - {name}")
    return 0

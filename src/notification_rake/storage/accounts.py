"""Connected buyer accounts — profile-scoped marketplace credentials."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from notification_rake.ingestion.connectors import SUPPORTED_PROVIDERS, ConnectorConfig


@dataclass(frozen=True)
class ConnectedAccount:
    id: str
    profile_id: str
    provider: str
    label: str
    config: dict[str, Any]
    enabled: bool
    last_sync_at: str | None
    last_status: str | None
    listings_synced: int


def new_profile_id() -> str:
    return str(uuid.uuid4())


def list_accounts(dsn: str, profile_id: str) -> list[ConnectedAccount]:
    import psycopg

    sql = """
        SELECT id, profile_id, provider, label, config, enabled,
               last_sync_at, last_status, listings_synced
        FROM metadata.connected_account
        WHERE profile_id = %(profile_id)s::uuid
        ORDER BY provider, label;
    """
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, {"profile_id": profile_id}).fetchall()
    return [_row_to_account(r) for r in rows]


def upsert_account(
    dsn: str,
    *,
    profile_id: str,
    provider: str,
    label: str,
    config: dict[str, Any],
    enabled: bool = True,
) -> ConnectedAccount:
    import psycopg

    provider = provider.lower().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported provider: {provider}")

    sql = """
        INSERT INTO metadata.connected_account (profile_id, provider, label, config, enabled)
        VALUES (%(profile_id)s::uuid, %(provider)s, %(label)s, %(config)s::jsonb, %(enabled)s)
        ON CONFLICT (profile_id, provider, label) DO UPDATE SET
            config = EXCLUDED.config,
            enabled = EXCLUDED.enabled,
            updated_at = now()
        RETURNING id, profile_id, provider, label, config, enabled,
                  last_sync_at, last_status, listings_synced;
    """
    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            sql,
            {
                "profile_id": profile_id,
                "provider": provider,
                "label": label or provider,
                "config": json.dumps(config),
                "enabled": enabled,
            },
        ).fetchone()
        conn.commit()
    return _row_to_account(row)


def delete_account(dsn: str, account_id: str, profile_id: str) -> bool:
    import psycopg

    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            """
            DELETE FROM metadata.connected_account
            WHERE id = %(id)s::uuid AND profile_id = %(profile_id)s::uuid
            RETURNING id;
            """,
            {"id": account_id, "profile_id": profile_id},
        ).fetchone()
        conn.commit()
    return row is not None


def mark_sync(dsn: str, account_id: str, *, status: str, count: int) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            UPDATE metadata.connected_account
            SET last_sync_at = now(), last_status = %(status)s,
                listings_synced = listings_synced + %(count)s, updated_at = now()
            WHERE id = %(id)s::uuid;
            """,
            {"id": account_id, "status": status, "count": count},
        )
        conn.commit()


def enabled_connector_configs(dsn: str, profile_id: str) -> list[ConnectorConfig]:
    accounts = [a for a in list_accounts(dsn, profile_id) if a.enabled]
    return [
        ConnectorConfig(provider=a.provider, label=a.label, config=a.config) for a in accounts
    ]


def _row_to_account(row: tuple[Any, ...]) -> ConnectedAccount:
    cfg = row[4]
    if not isinstance(cfg, dict):
        cfg = json.loads(cfg or "{}")
    return ConnectedAccount(
        id=str(row[0]),
        profile_id=str(row[1]),
        provider=row[2],
        label=row[3] or row[2],
        config=cfg,
        enabled=bool(row[5]),
        last_sync_at=row[6].isoformat() if row[6] else None,
        last_status=row[7],
        listings_synced=int(row[8] or 0),
    )

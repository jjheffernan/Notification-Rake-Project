"""Server-side scheduled vehicle searches (watchlist)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class ScheduledSearch:
    id: str
    profile_id: str | None
    name: str
    query_json: dict[str, Any]
    alert_enabled: bool
    enabled: bool
    interval_minutes: int
    ingest_routes: list[str]
    last_run_at: str | None
    next_run_at: str | None
    last_match_count: int | None
    last_new_count: int | None
    last_seen_ids: list[str]
    created_at: str


def _row_to_search(row: tuple[Any, ...]) -> ScheduledSearch:
    ingest = row[7]
    if isinstance(ingest, str):
        ingest = json.loads(ingest)
    seen = row[12]
    if isinstance(seen, str):
        seen = json.loads(seen)
    qj = row[3]
    if isinstance(qj, str):
        qj = json.loads(qj)
    return ScheduledSearch(
        id=str(row[0]),
        profile_id=str(row[1]) if row[1] else None,
        name=row[2],
        query_json=qj if isinstance(qj, dict) else {},
        alert_enabled=bool(row[4]),
        enabled=bool(row[5]),
        interval_minutes=int(row[6] or 360),
        ingest_routes=list(ingest or []),
        last_run_at=row[8].isoformat() if row[8] else None,
        next_run_at=row[9].isoformat() if row[9] else None,
        last_match_count=row[10],
        last_new_count=row[11],
        last_seen_ids=[str(i) for i in (seen or [])],
        created_at=row[13].isoformat() if row[13] else "",
    )


_SELECT = """
    SELECT id, profile_id, name, query_json, alert_enabled, enabled,
           interval_minutes, ingest_routes, last_run_at, next_run_at,
           last_match_count, last_new_count, last_seen_ids, created_at
    FROM metadata.saved_search
"""


def list_scheduled_searches(
    dsn: str,
    *,
    profile_id: str | None = None,
    enabled_only: bool = False,
) -> list[ScheduledSearch]:
    import psycopg

    where = ["TRUE"]
    params: dict[str, Any] = {}
    if profile_id:
        params["profile_id"] = profile_id
        where.append("profile_id = %(profile_id)s::uuid")
    if enabled_only:
        where.append("enabled = true")
    sql = f"{_SELECT} WHERE {' AND '.join(where)} ORDER BY created_at DESC"
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_search(r) for r in rows]


def get_scheduled_search(dsn: str, search_id: str) -> ScheduledSearch | None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            f"{_SELECT} WHERE id = %(id)s::uuid",
            {"id": search_id},
        ).fetchone()
    return _row_to_search(row) if row else None


def upsert_scheduled_search(
    dsn: str,
    *,
    profile_id: str | None,
    name: str,
    query_json: dict[str, Any],
    alert_enabled: bool = True,
    enabled: bool = True,
    interval_minutes: int = 360,
    ingest_routes: list[str] | None = None,
    search_id: str | None = None,
) -> ScheduledSearch:
    import psycopg

    interval_minutes = max(15, min(interval_minutes, 10_080))  # 15 min – 7 days
    routes = ingest_routes or []
    now = datetime.now(UTC)
    next_run = now + timedelta(minutes=interval_minutes)
    params: dict[str, Any] = {
        "id": search_id or str(uuid4()),
        "profile_id": profile_id,
        "name": name.strip() or "Watchlist search",
        "query_json": json.dumps(query_json),
        "alert_enabled": alert_enabled,
        "enabled": enabled,
        "interval_minutes": interval_minutes,
        "ingest_routes": json.dumps(routes),
        "next_run_at": next_run,
    }
    sql = """
        INSERT INTO metadata.saved_search (
            id, profile_id, name, query_json, alert_enabled, enabled,
            interval_minutes, ingest_routes, next_run_at
        ) VALUES (
            %(id)s::uuid, %(profile_id)s::uuid, %(name)s, %(query_json)s::jsonb,
            %(alert_enabled)s, %(enabled)s, %(interval_minutes)s,
            %(ingest_routes)s::jsonb, %(next_run_at)s
        )
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            query_json = EXCLUDED.query_json,
            alert_enabled = EXCLUDED.alert_enabled,
            enabled = EXCLUDED.enabled,
            interval_minutes = EXCLUDED.interval_minutes,
            ingest_routes = EXCLUDED.ingest_routes,
            next_run_at = COALESCE(metadata.saved_search.next_run_at, EXCLUDED.next_run_at)
        RETURNING id, profile_id, name, query_json, alert_enabled, enabled,
                  interval_minutes, ingest_routes, last_run_at, next_run_at,
                  last_match_count, last_new_count, last_seen_ids, created_at;
    """
    with psycopg.connect(dsn) as conn:
        row = conn.execute(sql, params).fetchone()
        conn.commit()
    return _row_to_search(row)


def delete_scheduled_search(dsn: str, search_id: str, profile_id: str | None = None) -> bool:
    import psycopg

    params: dict[str, Any] = {"id": search_id}
    where = "id = %(id)s::uuid"
    if profile_id:
        params["profile_id"] = profile_id
        where += " AND profile_id = %(profile_id)s::uuid"
    with psycopg.connect(dsn) as conn:
        cur = conn.execute(f"DELETE FROM metadata.saved_search WHERE {where}", params)
        conn.commit()
    return cur.rowcount > 0


def list_due_searches(
    dsn: str,
    *,
    profile_id: str | None = None,
    limit: int = 50,
) -> list[ScheduledSearch]:
    import psycopg

    where = [
        "enabled = true",
        "(next_run_at IS NULL OR next_run_at <= now())",
    ]
    params: dict[str, Any] = {"limit": limit}
    if profile_id:
        where.append("profile_id = %(profile_id)s::uuid")
        params["profile_id"] = profile_id
    sql = f"""
        {_SELECT}
        WHERE {' AND '.join(where)}
        ORDER BY next_run_at NULLS FIRST
        LIMIT %(limit)s;
    """
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_search(r) for r in rows]


def record_search_run(
    dsn: str,
    search_id: str,
    *,
    match_count: int,
    new_count: int,
    seen_ids: list[str],
    interval_minutes: int,
) -> None:
    import psycopg

    cap_ids = seen_ids[:500]
    next_run = datetime.now(UTC) + timedelta(minutes=interval_minutes)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            UPDATE metadata.saved_search SET
                last_run_at = now(),
                next_run_at = %(next_run_at)s,
                last_match_count = %(match_count)s,
                last_new_count = %(new_count)s,
                last_seen_ids = %(seen_ids)s::jsonb
            WHERE id = %(id)s::uuid;
            """,
            {
                "id": search_id,
                "next_run_at": next_run,
                "match_count": match_count,
                "new_count": new_count,
                "seen_ids": json.dumps(cap_ids),
            },
        )
        conn.commit()

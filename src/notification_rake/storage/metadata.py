"""Job run and operational metadata tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JobRun:
    id: str
    job_name: str
    status: str
    started_at: str
    finished_at: str | None
    fetched: int | None
    matched: int | None
    upserted: int | None
    new_listings: int | None
    alerted: int | None
    error_message: str | None


def start_job(dsn: str, job_name: str) -> str:
    import psycopg

    with psycopg.connect(dsn) as conn:
        row = conn.execute(
            """
            INSERT INTO metadata.job_runs (job_name, status)
            VALUES (%(job_name)s, 'running')
            RETURNING id;
            """,
            {"job_name": job_name},
        ).fetchone()
        conn.commit()
    return str(row[0])


def finish_job(
    dsn: str,
    job_id: str,
    *,
    status: str,
    fetched: int | None = None,
    matched: int | None = None,
    upserted: int | None = None,
    new_listings: int | None = None,
    alerted: int | None = None,
    error_message: str | None = None,
) -> None:
    import psycopg

    params: dict[str, Any] = {
        "job_id": job_id,
        "status": status,
        "error_message": error_message,
        "fetched": fetched,
        "matched": matched,
        "upserted": upserted,
        "new_listings": new_listings,
        "alerted": alerted,
    }
    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            UPDATE metadata.job_runs SET
                status = %(status)s,
                finished_at = now(),
                fetched = %(fetched)s,
                matched = %(matched)s,
                upserted = %(upserted)s,
                new_listings = %(new_listings)s,
                alerted = %(alerted)s,
                error_message = %(error_message)s
            WHERE id = %(job_id)s;
            """,
            params,
        )
        if upserted:
            conn.execute(
                """
                INSERT INTO metadata.sync_status (layer, records_synced, notes)
                VALUES ('search', %(count)s, 'vehicle_listing upsert');
                """,
                {"count": upserted},
            )
        conn.commit()


def list_job_runs(dsn: str, *, limit: int = 20) -> list[JobRun]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            """
            SELECT id, job_name, status, started_at, finished_at,
                   fetched, matched, upserted, new_listings, alerted, error_message
            FROM metadata.job_runs
            ORDER BY started_at DESC
            LIMIT %(limit)s;
            """,
            {"limit": limit},
        ).fetchall()
    return [
        JobRun(
            id=str(r[0]),
            job_name=r[1],
            status=r[2],
            started_at=r[3].isoformat() if r[3] else "",
            finished_at=r[4].isoformat() if r[4] else None,
            fetched=r[5],
            matched=r[6],
            upserted=r[7],
            new_listings=r[8],
            alerted=r[9],
            error_message=r[10],
        )
        for r in rows
    ]


def record_api_usage(
    dsn: str,
    *,
    endpoint: str,
    method: str = "GET",
    status_code: int | None = None,
    duration_ms: int | None = None,
) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            INSERT INTO metadata.api_usage (endpoint, method, status_code, duration_ms)
            VALUES (%(endpoint)s, %(method)s, %(status_code)s, %(duration_ms)s);
            """,
            {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        conn.commit()

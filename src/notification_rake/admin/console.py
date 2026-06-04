"""Runtime administration — service health, layer stats, operational actions."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from dataclasses import dataclass
from typing import Any

import httpx

from notification_rake.config import settings
from notification_rake.integrations.hasura import track_tables
from notification_rake.storage.db import add_vehicle_model, check_connection, seed_catalog
from notification_rake.storage.metadata import list_job_runs

ALLOWED_ACTIONS: frozenset[str] = frozenset(
    {
        "health",
        "pipeline",
        "seed",
        "hasura_track",
        "ingest",
        "normalize",
        "upsert",
        "search_reindex",
        "ingest_all",
        "ingest_copart",
        "ingest_yahoo",
        "ingest_europe",
        "ingest_carsandbids",
        "ingest_us_retail",
        "ingest_us_auction",
        "ingest_jp",
        "ingest_uk",
        "ingest_de",
        "run_scheduled_searches",
    }
)

ROUTE_INGEST_ACTIONS: dict[str, str] = {
    "ingest_us_retail": "us-retail",
    "ingest_us_auction": "us-auction",
    "ingest_jp": "jp",
    "ingest_uk": "uk",
    "ingest_de": "de",
}


@dataclass(frozen=True)
class ServiceStatus:
    key: str
    label: str
    status: str  # ok | fail | skip
    url: str
    detail: str
    console_url: str | None = None


@dataclass(frozen=True)
class SourceInfo:
    id: int
    name: str
    base_url: str | None
    enabled: bool
    last_run_at: str | None
    last_status: str | None
    listings_seen: int


@dataclass(frozen=True)
class LayerStats:
    search_listings: int
    raw_listings: int
    catalog_models: int
    job_runs: int
    sources: int


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    action: str
    message: str


def _http_status(url: str, path: str = "") -> tuple[str, str]:
    target = f"{url.rstrip('/')}{path}"
    try:
        resp = httpx.get(target, timeout=5.0)
        resp.raise_for_status()
        return "ok", f"HTTP {resp.status_code}"
    except Exception as exc:
        return "fail", str(exc)


def check_services() -> list[ServiceStatus]:
    """Health of stack components (container network URLs)."""
    services: list[ServiceStatus] = []

    try:
        ok = check_connection(settings.database_url)
        host = settings.database_url.split("@")[-1]
        services.append(
            ServiceStatus(
                "postgres",
                "PostgreSQL / PostGIS",
                "ok" if ok else "fail",
                host,
                host,
                settings.adminer_url,
            )
        )
    except Exception as exc:
        services.append(
            ServiceStatus(
                "postgres",
                "PostgreSQL / PostGIS",
                "fail",
                "db",
                str(exc),
                settings.adminer_url,
            )
        )

    status, detail = _http_status(settings.hasura_url, "/healthz")
    services.append(
        ServiceStatus(
            "hasura",
            "Hasura GraphQL",
            status,
            settings.hasura_url,
            detail,
            f"{settings.hasura_url.rstrip('/')}/console",
        )
    )

    status, detail = _http_status(settings.gotify_url, "/")
    services.append(
        ServiceStatus(
            "gotify",
            "Gotify push",
            status,
            settings.gotify_url,
            detail,
            settings.gotify_public_url,
        )
    )

    from notification_rake.search.meilisearch_client import check_health

    ok, detail = check_health()
    meili_status = "ok" if ok else ("skip" if not settings.meilisearch_url else "fail")
    services.append(
        ServiceStatus(
            "meilisearch",
            "Meilisearch",
            meili_status,
            settings.meilisearch_url,
            detail,
            settings.meilisearch_public_url,
        )
    )

    status, detail = _http_status(settings.prometheus_internal_url, "/-/healthy")
    services.append(
        ServiceStatus(
            "prometheus",
            "Prometheus",
            status if status == "ok" else "skip",
            settings.prometheus_internal_url,
            detail,
            settings.grafana_url,
        )
    )

    status, detail = _http_status(settings.metabase_internal_url, "/api/health")
    services.append(
        ServiceStatus(
            "metabase",
            "Metabase analytics",
            status if status == "ok" else "skip",
            settings.metabase_internal_url,
            detail,
            settings.metabase_url,
        )
    )

    status, detail = _http_status(settings.jupyter_internal_url, "/api")
    services.append(
        ServiceStatus(
            "jupyter",
            "JupyterLab",
            status if status == "ok" else "skip",
            settings.jupyter_internal_url,
            detail,
            settings.jupyter_url,
        )
    )

    return services


def layer_stats(dsn: str | None = None) -> LayerStats:
    import psycopg

    dsn = dsn or settings.database_url
    sql = """
        SELECT
            (SELECT COUNT(*) FROM public.vehicle_listing),
            (SELECT COUNT(*) FROM listings.listing),
            (SELECT COUNT(*) FROM public.vehicle_model),
            (SELECT COUNT(*) FROM metadata.job_runs),
            (SELECT COUNT(*) FROM listings.source);
    """
    try:
        with psycopg.connect(dsn) as conn:
            row = conn.execute(sql).fetchone()
        return LayerStats(
            search_listings=int(row[0]),
            raw_listings=int(row[1]),
            catalog_models=int(row[2]),
            job_runs=int(row[3]),
            sources=int(row[4]),
        )
    except Exception:
        return LayerStats(0, 0, 0, 0, 0)


def list_sources(dsn: str | None = None) -> list[SourceInfo]:
    import psycopg

    dsn = dsn or settings.database_url
    sql = """
        SELECT s.id, s.name, s.base_url, s.enabled,
               c.last_run_at, c.last_status, c.listings_seen
        FROM listings.source s
        LEFT JOIN metadata.crawler_status c ON c.source_id = s.id
        ORDER BY s.name;
    """
    try:
        with psycopg.connect(dsn) as conn:
            rows = conn.execute(sql).fetchall()
    except Exception:
        return []
    return [
        SourceInfo(
            id=int(r[0]),
            name=r[1],
            base_url=r[2],
            enabled=bool(r[3]),
            last_run_at=r[4].isoformat() if r[4] else None,
            last_status=r[5],
            listings_seen=int(r[6] or 0),
        )
        for r in rows
    ]


def set_source_enabled(dsn: str, source_id: int, *, enabled: bool) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE listings.source SET enabled = %(enabled)s WHERE id = %(id)s;",
            {"id": source_id, "enabled": enabled},
        )
        conn.commit()


def add_catalog_model(dsn: str, make: str, model: str) -> ActionResult:
    try:
        model_id = add_vehicle_model(dsn, make.strip(), model.strip())
        return ActionResult(True, "add_model", f"{make}/{model} → model_id={model_id}")
    except Exception as exc:
        return ActionResult(False, "add_model", str(exc))


def list_recent_syncs(dsn: str | None = None, *, limit: int = 10) -> list[dict[str, Any]]:
    import psycopg

    dsn = dsn or settings.database_url
    try:
        with psycopg.connect(dsn) as conn:
            rows = conn.execute(
                """
                SELECT layer, records_synced, notes, last_sync_at
                FROM metadata.sync_status
                ORDER BY last_sync_at DESC
                LIMIT %(limit)s;
                """,
                {"limit": limit},
            ).fetchall()
    except Exception:
        return []
    return [
        {
            "layer": r[0],
            "records_synced": r[1],
            "notes": r[2],
            "last_sync_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]


def admin_overview(dsn: str | None = None) -> dict[str, Any]:
    dsn = dsn or settings.database_url
    return {
        "services": [s.__dict__ for s in check_services()],
        "layers": layer_stats(dsn).__dict__,
        "sources": [s.__dict__ for s in list_sources(dsn)],
        "syncs": list_recent_syncs(dsn),
        "jobs": [j.__dict__ for j in list_job_runs(dsn, limit=10)],
        "actions": sorted(ALLOWED_ACTIONS),
    }


def execute_action(action: str, dsn: str | None = None) -> ActionResult:
    if action not in ALLOWED_ACTIONS:
        return ActionResult(False, action, f"unknown action: {action}")

    dsn = dsn or settings.database_url

    try:
        if action == "pipeline":
            from notification_rake.workflow.routes import run_route

            run = run_route("us-retail", dsn=dsn)
            result = run.result
            msg = (
                f"route=us-retail fetched={result.fetched} raw={result.raw_stored} "
                f"upserted={result.upserted} new={result.new} alerted={result.alerted}"
            )
            return ActionResult(result.fetched > 0, action, msg)

        if action in ROUTE_INGEST_ACTIONS:
            from notification_rake.workflow.routes import run_route

            slug = ROUTE_INGEST_ACTIONS[action]
            run = run_route(slug, dsn=dsn)
            result = run.result
            msg = (
                f"route={slug} fetched={result.fetched} upserted={result.upserted} "
                f"new={result.new} sources={','.join(run.sources) or 'none'}"
            )
            return ActionResult(result.upserted > 0, action, msg)

        if action == "seed":
            count = seed_catalog(dsn)
            return ActionResult(True, action, f"catalog seeded ({count} models)")

        if action == "hasura_track":
            tracked = track_tables()
            return ActionResult(True, action, f"tracked {len(tracked)} tables")

        if action == "search_reindex":
            from notification_rake.search.meilisearch_client import sync_documents

            count = sync_documents(dsn, None)
            return ActionResult(True, action, f"indexed {count} listings in Meilisearch")

        if action == "ingest_all":
            from notification_rake.workflow.routes import merge_route_results, run_all_routes

            outcomes = run_all_routes(dsn=dsn, continue_on_error=True)
            result = merge_route_results(outcomes)
            routes_summary = ", ".join(
                f"{slug}={run.result.upserted}" for slug, run in outcomes.items()
            )
            msg = (
                f"fetched={result.fetched} upserted={result.upserted} "
                f"new={result.new} alerted={result.alerted} [{routes_summary}]"
            )
            return ActionResult(result.upserted > 0, action, msg)

        if action == "ingest_copart":
            from notification_rake.workflow.multi_source import ingest_copart, sync_listings

            items = ingest_copart()
            ids = sync_listings(items, dsn=dsn)
            return ActionResult(bool(ids), action, f"copart upserted={len(ids)}")

        if action == "ingest_yahoo":
            from notification_rake.workflow.multi_source import ingest_yahoo, sync_listings

            items = ingest_yahoo()
            ids = sync_listings(items, dsn=dsn)
            return ActionResult(bool(ids), action, f"yahoo upserted={len(ids)}")

        if action == "ingest_europe":
            from notification_rake.workflow.routes import merge_route_results, run_all_routes

            outcomes = run_all_routes(dsn=dsn, routes=["uk", "de"], continue_on_error=True)
            result = merge_route_results(outcomes)
            uk = outcomes.get("uk")
            de = outcomes.get("de")
            return ActionResult(
                result.upserted > 0,
                action,
                f"europe upserted={result.upserted} "
                f"uk={uk.result.upserted if uk else 0} de={de.result.upserted if de else 0}",
            )

        if action == "ingest_carsandbids":
            from notification_rake.workflow.multi_source import ingest_carsandbids, sync_listings

            items = ingest_carsandbids()
            ids = sync_listings(items, dsn=dsn)
            return ActionResult(bool(ids), action, f"carsandbids upserted={len(ids)}")

        if action == "run_scheduled_searches":
            from notification_rake.workflow.scheduled_batch import run_scheduled_batch

            result = run_scheduled_batch(dsn=dsn)
            msg = (
                f"searches={result.searches_run} new={result.total_new_matches} "
                f"alerted={result.total_alerted} ingest_upserted={result.ingest_upserted}"
            )
            return ActionResult(result.searches_run >= 0, action, msg)

        if action == "health":
            services = check_services()
            failed = [s.label for s in services if s.status == "fail"]
            if failed:
                return ActionResult(False, action, f"unhealthy: {', '.join(failed)}")
            return ActionResult(True, action, "all core services reachable")

        from notification_rake import run_script

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run_script(action)
        output = buf.getvalue().strip() or f"exit {code}"
        return ActionResult(code == 0, action, output)
    except Exception as exc:
        return ActionResult(False, action, str(exc))

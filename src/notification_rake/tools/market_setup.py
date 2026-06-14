"""Automate onboarding of new ingest markets — SQL, registry snippets, audit."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DB_INIT = _REPO_ROOT / "db" / "init"
_REGIONS_PY = _REPO_ROOT / "src" / "notification_rake" / "models" / "regions.py"
_INGEST_ROUTES_PY = _REPO_ROOT / "src" / "notification_rake" / "models" / "ingest_routes.py"
_MIGRATIONS_PY = _REPO_ROOT / "src" / "notification_rake" / "storage" / "migrations.py"


@dataclass(frozen=True)
class MarketSource:
    """One marketplace source slug registered in listings.source."""

    name: str
    base_url: str = ""


@dataclass
class MarketSpec:
    """Definition of a market/route to add to the ingest stack."""

    route_slug: str
    route_label: str
    country_code: str
    sources: list[MarketSource]
    description: str = ""
    region_label: str | None = None
    region_center: tuple[float, float] | None = None
    add_to_bulk_ingest: bool = True
    fetch_strategy: str = "stub"  # stub | europe | connected | custom
    migration_note: str = ""


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class MarketPlan:
    spec: MarketSpec
    migration_filename: str
    migration_sql: str
    regions_snippet: str
    ingest_routes_snippet: str
    bulk_routes_snippet: str
    workflow_fetch_snippet: str
    connectors_snippet: str
    admin_action_snippet: str
    ingest_script: str
    ingestion_stub: str
    checklist: list[str] = field(default_factory=list)


def normalize_slug(value: str) -> str:
    text = value.strip().lower().replace("-", "_")
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    return text.strip("_")


def next_migration_number() -> int:
    nums: list[int] = []
    for path in _DB_INIT.glob("*.sql"):
        match = re.match(r"^(\d+)_", path.name)
        if match:
            nums.append(int(match.group(1)))
    return max(nums, default=0) + 1


def _source_names(spec: MarketSpec) -> list[str]:
    return [normalize_slug(s.name) for s in spec.sources]


def generate_migration_sql(
    spec: MarketSpec,
    *,
    migration_num: int | None = None,
) -> tuple[str, str]:
    num = migration_num or next_migration_number()
    slug = normalize_slug(spec.route_slug)
    lines = [
        f"-- Market sources: {spec.route_label} ({spec.country_code})",
        "",
        "INSERT INTO listings.source (name, base_url, country_code) VALUES",
    ]
    values = []
    for src in spec.sources:
        name = normalize_slug(src.name)
        url = src.base_url.replace("'", "''")
        values.append(f"    ('{name}', '{url}', '{spec.country_code.upper()}')")
    lines.append(",\n".join(values))
    lines.append("ON CONFLICT (name) DO UPDATE SET")
    lines.append("    base_url = EXCLUDED.base_url,")
    lines.append("    country_code = EXCLUDED.country_code;")
    if spec.migration_note:
        lines.extend(["", f"-- {spec.migration_note}"])
    return "\n".join(lines) + "\n", f"{num:03d}_{slug}_market.sql"


def generate_regions_snippet(spec: MarketSpec) -> str:
    lines = ["# Add to SOURCE_COUNTRY in models/regions.py:"]
    for name in _source_names(spec):
        lines.append(f'    "{name}": "{spec.country_code.upper()}",')
    if spec.region_label and spec.region_center:
        lon, lat = spec.region_center
        code = spec.country_code.upper()
        lines.extend(
            [
                "",
                "# Add to REGION_LABELS:",
                f'    "{code}": "{spec.region_label}",',
                "",
                "# Add to REGION_CENTERS (lon, lat):",
                f'    "{code}": ({lon}, {lat}),',
            ]
        )
    return "\n".join(lines)


def generate_ingest_routes_snippet(spec: MarketSpec) -> str:
    slug = normalize_slug(spec.route_slug)
    sources = ", ".join(f'"{n}"' for n in _source_names(spec))
    desc = spec.description or f"{spec.route_label} marketplace ingest"
    return f'''
    "{slug}": IngestRoute(
        slug="{slug}",
        label="{spec.route_label}",
        sources=frozenset({{{sources}}}),
        country="{spec.country_code.upper()}",
        description="{desc}",
    ),'''.strip()


def generate_bulk_routes_snippet(spec: MarketSpec) -> str:
    if not spec.add_to_bulk_ingest:
        return "# Route not marked for bulk ingest — skip bulk_ingest_route_slugs()"
    slug = normalize_slug(spec.route_slug)
    return f'# Append "{slug}" to bulk_ingest_route_slugs() return list in ingest_routes.py'


def generate_workflow_snippet(spec: MarketSpec) -> str:
    slug = normalize_slug(spec.route_slug)
    if spec.fetch_strategy == "europe":
        return f'''
    if slug == "{slug}":
        if not settings.eu_marketplaces_enabled:
            return []
        return fetch_europe_listings(
            sources=sorted(sources_for_route("{slug}") or ()),
            limit=settings.eu_ingest_limit,
        )'''.strip()
    if spec.fetch_strategy == "connected":
        return f'''
    if slug == "{slug}":
        if not profile_id:
            return []
        configs = enabled_connector_configs(settings.database_url, profile_id)
        return fetch_all_connected(configs)'''.strip()
    return f'''
    if slug == "{slug}":
        # TODO: wire fetch_{slug}() in ingestion/{slug}/
        raise NotImplementedError("fetch not implemented for route: {slug}")'''.strip()


def generate_connectors_snippet(spec: MarketSpec) -> str:
    names = _source_names(spec)
    lines = ["# Add to SUPPORTED_PROVIDERS in ingestion/connectors.py:"]
    for name in names:
        lines.append(f'        "{name}",')
    lines.append("")
    lines.append("# Add fetch branch in fetch_from_connector() and ACCOUNT_FIELDS in public.py")
    return "\n".join(lines)


def generate_admin_snippet(spec: MarketSpec) -> str:
    slug = normalize_slug(spec.route_slug)
    action = f"ingest_{slug}"
    return f'''
# admin/console.py ALLOWED_ACTIONS + execute_action:
"{action}": "{slug}",

if action == "{action}":
    from notification_rake.workflow.routes import run_route
    run = run_route("{slug}", dsn=dsn)
    ...'''.strip()


def generate_ingest_script(spec: MarketSpec) -> str:
    slug = normalize_slug(spec.route_slug)
    return f'''"""Run {spec.route_label} ingest route."""

from __future__ import annotations

from ingest._common import run_route_script

ALIASES = ("ingest_{slug}",)


def run() -> int:
    return run_route_script("{slug}")
'''


def generate_ingestion_stub(spec: MarketSpec) -> str:
    slug = normalize_slug(spec.route_slug)
    return f'''"""{spec.route_label} ingestion — stub module (implement fetch + normalize)."""

from __future__ import annotations

from notification_rake.models.listing import VehicleListing


def fetch_listings(*, limit: int = 50) -> list[VehicleListing]:
    """Fetch listings from {spec.route_label} sources. Replace with live client."""
    raise NotImplementedError("Implement {slug} fetch_listings()")
'''


def plan_market(spec: MarketSpec) -> MarketPlan:
    migration_sql, migration_filename = generate_migration_sql(spec)
    checklist = [
        f"Apply SQL migration: db/init/{migration_filename}",
        "Register migration in storage/migrations.py _MIGRATION_FILES",
        "Patch models/regions.py (SOURCE_COUNTRY + region if new)",
        "Patch models/ingest_routes.py (INGEST_ROUTES + bulk list)",
        "Wire fetch_route() in workflow/routes.py",
        "Add SUPPORTED_PROVIDERS + connector in ingestion/connectors.py",
        "Add ACCOUNT_FIELDS entry in web/blueprints/public.py (if connected)",
        f"Create scripts/ingest/routes/{normalize_slug(spec.route_slug)}.py",
        f"Implement ingestion/{normalize_slug(spec.route_slug)}/ module",
        "Add admin action in admin/console.py",
        "Add tests in tests/test_ingest_routes.py",
        "Run: make test && docker compose run --rm app ingest_<route>",
    ]
    return MarketPlan(
        spec=spec,
        migration_filename=migration_filename,
        migration_sql=migration_sql,
        regions_snippet=generate_regions_snippet(spec),
        ingest_routes_snippet=generate_ingest_routes_snippet(spec),
        bulk_routes_snippet=generate_bulk_routes_snippet(spec),
        workflow_fetch_snippet=generate_workflow_snippet(spec),
        connectors_snippet=generate_connectors_snippet(spec),
        admin_action_snippet=generate_admin_snippet(spec),
        ingest_script=generate_ingest_script(spec),
        ingestion_stub=generate_ingestion_stub(spec),
        checklist=checklist,
    )


def register_sources(dsn: str, sources: list[MarketSource], *, country_code: str) -> int:
    """Upsert listings.source rows for a market."""
    import psycopg

    sql = """
        INSERT INTO listings.source (name, base_url, country_code)
        VALUES (%(name)s, %(base_url)s, %(country)s)
        ON CONFLICT (name) DO UPDATE SET
            base_url = COALESCE(EXCLUDED.base_url, listings.source.base_url),
            country_code = EXCLUDED.country_code
        RETURNING id;
    """
    count = 0
    with psycopg.connect(dsn) as conn:
        for src in sources:
            conn.execute(
                sql,
                {
                    "name": normalize_slug(src.name),
                    "base_url": src.base_url or None,
                    "country": country_code.upper(),
                },
            )
            count += 1
        conn.commit()
    return count


def _file_contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    return needle in path.read_text(encoding="utf-8")


def audit_market(spec: MarketSpec) -> list[CheckResult]:
    """Check which onboarding steps are already done."""
    slug = normalize_slug(spec.route_slug)
    results: list[CheckResult] = []

    for src in spec.sources:
        name = normalize_slug(src.name)
        results.append(
            CheckResult(
                f"SOURCE_COUNTRY[{name}]",
                _file_contains(_REGIONS_PY, f'"{name}":'),
            )
        )

    results.append(
        CheckResult(
            f'INGEST_ROUTES["{slug}"]',
            _file_contains(_INGEST_ROUTES_PY, f'"{slug}":'),
        )
    )
    if spec.add_to_bulk_ingest:
        results.append(
            CheckResult(
                "bulk_ingest_route_slugs",
                _file_contains(_INGEST_ROUTES_PY, f'"{slug}"')
                and "bulk_ingest_route_slugs" in _INGEST_ROUTES_PY.read_text(encoding="utf-8"),
            )
        )

    migration_glob = list(_DB_INIT.glob(f"*_{slug}_market.sql")) + list(
        _DB_INIT.glob(f"*_{slug}.sql")
    )
    results.append(
        CheckResult(
            "db/init migration file",
            bool(migration_glob),
            detail=migration_glob[0].name if migration_glob else "missing",
        )
    )

    script_path = _REPO_ROOT / "scripts" / "ingest" / "routes" / f"{slug}.py"
    results.append(CheckResult(f"scripts/ingest/routes/{slug}.py", script_path.is_file()))

    ingest_mod = _REPO_ROOT / "src" / "notification_rake" / "ingestion" / slug
    results.append(
        CheckResult(
            f"ingestion/{slug}/ module",
            ingest_mod.is_dir(),
            detail=str(ingest_mod.relative_to(_REPO_ROOT)) if ingest_mod.is_dir() else "missing",
        )
    )

    return results


def write_artifacts(plan: MarketPlan, output_dir: Path | None = None) -> Path:
    """Write generated SQL, scripts, and snippets to disk for review."""
    slug = normalize_slug(plan.spec.route_slug)
    out = output_dir or (_REPO_ROOT / "notebooks" / "out" / f"market_{slug}")
    out.mkdir(parents=True, exist_ok=True)

    routes_dir = out / "routes"
    routes_dir.mkdir(exist_ok=True)
    (out / plan.migration_filename).write_text(plan.migration_sql, encoding="utf-8")
    (routes_dir / f"{slug}.py").write_text(plan.ingest_script, encoding="utf-8")
    (out / f"ingestion_{slug}_stub.py").write_text(plan.ingestion_stub, encoding="utf-8")

    readme = [
        f"# Market onboarding: {plan.spec.route_label}",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        "## Checklist",
        *[f"- [ ] {item}" for item in plan.checklist],
        "",
        "## regions.py",
        "```python",
        plan.regions_snippet,
        "```",
        "",
        "## ingest_routes.py",
        "```python",
        plan.ingest_routes_snippet,
        "```",
        "",
        plan.bulk_routes_snippet,
        "",
        "## workflow/routes.py",
        "```python",
        plan.workflow_fetch_snippet,
        "```",
        "",
        "## connectors.py",
        "```python",
        plan.connectors_snippet,
        "```",
        "",
        "## admin",
        "```python",
        plan.admin_action_snippet,
        "```",
    ]
    (out / "README.md").write_text("\n".join(readme), encoding="utf-8")
    return out


def print_plan_summary(plan: MarketPlan) -> None:
    """Pretty-print plan for notebooks."""
    print(f"Market: {plan.spec.route_label} ({plan.spec.route_slug})")
    print(f"Migration: db/init/{plan.migration_filename}")
    print(f"Sources: {', '.join(_source_names(plan.spec))}")
    print("\n--- Checklist ---")
    for i, item in enumerate(plan.checklist, 1):
        print(f"  {i}. {item}")
    print("\nArtifacts written via write_artifacts(plan)")

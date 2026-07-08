# Twelve-Factor App Compliance

Reference checklist for [The Twelve-Factor App](https://12factor.net/). Score each factor: **Compliant**, **Partial**, or **Gap**. Target ≥90% before public production.

**Last audited:** 2026-07-08 (post Phase 0–2 merge)

---

## I. Codebase

**One codebase, many deploys.**

| Status | Evidence |
|--------|----------|
| **Compliant** | Single Git repo; `docker-compose.yml` (local) and `deploy/coolify/docker-compose.yml` (prod) from same tree; CI builds same `docker/Dockerfile` targets. |

---

## II. Dependencies

**Explicitly declare and isolate.**

| Status | Evidence |
|--------|----------|
| **Compliant** | `pyproject.toml` with `[project.dependencies]` and `[project.optional-dependencies] dev`; Docker multi-stage builds; pip install in CI; Dependabot + pip-audit job. |

---

## III. Config

**Store config in the environment.**

| Status | Evidence |
|--------|----------|
| **Partial** | `config.Settings` via pydantic-settings; `.env.example` documents vars; `RAKE_ENV=production` rejects placeholder secrets; `configure_logging()` applies `LOG_LEVEL`. |

**Remaining:** `CREDENTIAL_ENCRYPTION_KEY` can derive from `DASHBOARD_SECRET_KEY` in dev only — document rotation path.

---

## IV. Backing services

**Treat as attached resources.**

| Status | Evidence |
|--------|----------|
| **Partial** | Postgres, Hasura, Gotify, Meilisearch referenced by URL env vars; Coolify compose includes `db`, `hasura`, `gotify`, `meilisearch`, `dashboard`, `app`. |

**Remaining:** No Redis/worker backing service yet.

---

## V. Build, release, run

**Strictly separate stages.**

| Status | Evidence |
|--------|----------|
| **Partial** | Docker `dashboard` and `app` targets; CI builds images; Coolify webhook on `main`. |

**Gaps:** No immutable release tagging; compose on server may pull `latest` without recorded artifact version.

---

## VI. Processes

**Execute as stateless processes.**

| Status | Evidence |
|--------|----------|
| **Partial** | Flask/gunicorn dashboard is stateless; admin session in signed cookie. Buyer `profile_id` is client-held UUID. |

**Gaps:** Scheduled batch runs in-request (no worker queue).

---

## VII. Port binding

**Export services via port binding.**

| Status | Evidence |
|--------|----------|
| **Compliant** | Dashboard binds `DASHBOARD_PORT`; local compose uses `127.0.0.1` bindings; Traefik labels on Coolify `dashboard`, `hasura`, `gotify`. |

---

## VIII. Concurrency

**Scale out via process model.**

| Status | Evidence |
|--------|----------|
| **Gap** | Single gunicorn process in dashboard container; ingest/cron via manual scripts or API trigger; no Redis/Celery worker (`PLAN.md` Phase 3). |

---

## IX. Disposability

**Fast startup and graceful shutdown.**

| Status | Evidence |
|--------|----------|
| **Partial** | DB healthchecks in compose; gunicorn handles SIGTERM; `/health` returns 503 when DB or Meilisearch degraded. |

**Gaps:** No graceful drain for in-flight scheduled batch.

---

## X. Dev/prod parity

**Keep dev and production similar.**

| Status | Evidence |
|--------|----------|
| **Partial** | Coolify compose now mirrors local core: `dashboard`, `app`, `meilisearch`, `db`, `hasura`, `gotify`. Local `dev-tools` profile (Jupyter, Adminer) not in prod — intentional. |

---

## XI. Logs

**Treat logs as event streams.**

| Status | Evidence |
|--------|----------|
| **Partial** | stdout logging; `LOG_LEVEL` wired via `configure_logging()`. |

**Gaps:** No JSON log format for aggregation; Gotify token may appear in URLs at WARNING+.

---

## XII. Admin processes

**Run as one-off processes.**

| Status | Evidence |
|--------|----------|
| **Partial** | `scripts/` for ingest, catalog, ops; admin console triggers pipeline actions; Jupyter for notebooks. |

**Gaps:** Some admin actions run inside web request lifecycle; no documented one-off job runner in production compose.

---

## Summary matrix

| Factor | Status |
|--------|--------|
| I Codebase | Compliant |
| II Dependencies | Compliant |
| III Config | Partial |
| IV Backing services | Partial |
| V Build/release/run | Partial |
| VI Processes | Partial |
| VII Port binding | Compliant |
| VIII Concurrency | Gap |
| IX Disposability | Partial |
| X Dev/prod parity | Partial |
| XI Logs | Partial |
| XII Admin processes | Partial |

**Compliance rate:** 3 Compliant + 8 Partial + 1 Gap ≈ **76%** (Partial ≈ 0.58 weight).

**Priority fixes:** VIII (worker for scheduled ingest), V (release tagging), XI (JSON logs optional).

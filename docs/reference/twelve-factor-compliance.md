# Twelve-Factor App Compliance

Reference checklist for [The Twelve-Factor App](https://12factor.net/). Score each factor: **Compliant**, **Partial**, or **Gap**. Target ≥90% before public production.

---

## I. Codebase

**One codebase, many deploys.**

| Status | Evidence |
|--------|----------|
| **Compliant** | Single Git repo; `docker-compose.yml` (local) and `deploy/coolify/docker-compose.yml` (prod) from same tree; CI builds same `docker/Dockerfile` targets. |

**Gaps:** Coolify compose is not a full deploy of the app surface (missing `dashboard`, `app`, `meilisearch`).

---

## II. Dependencies

**Explicitly declare and isolate.**

| Status | Evidence |
|--------|----------|
| **Compliant** | `pyproject.toml` with `[project.dependencies]` and `[project.optional-dependencies] dev`; Docker multi-stage builds; pip install in CI. |

---

## III. Config

**Store config in the environment.**

| Status | Evidence |
|--------|----------|
| **Partial** | `config.Settings` via pydantic-settings; `.env.example` documents vars. |

**Gaps:**
- Default `change-me` secrets not rejected at startup in production.
- `LOG_LEVEL` defined but not applied to Python logging.
- Some paths hardcoded in docs vs env (`RAKE_SCRIPTS_DIR` optional).

---

## IV. Backing services

**Treat as attached resources.**

| Status | Evidence |
|--------|----------|
| **Partial** | Postgres, Hasura, Gotify, Meilisearch referenced by URL env vars; `search_engine=auto` switches Postgres vs Meilisearch. |

**Gaps:** Coolify stack does not attach Meilisearch or app worker to the same network as full local stack.

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

**Gaps:** No horizontal scale story; scheduled batch runs in-request (no worker queue).

---

## VII. Port binding

**Export services via port binding.**

| Status | Evidence |
|--------|----------|
| **Compliant** | Dashboard binds `DASHBOARD_PORT`; local compose uses `127.0.0.1` bindings; Traefik labels on Coolify services. |

---

## VIII. Concurrency

**Scale out via process model.**

| Status | Evidence |
|--------|----------|
| **Gap** | Single gunicorn process in dashboard container; ingest/cron via manual scripts or API trigger; no Redis/Celery worker (noted in `docs/deploy.md` scale path). |

---

## IX. Disposability

**Fast startup and graceful shutdown.**

| Status | Evidence |
|--------|----------|
| **Partial** | DB healthchecks in compose; gunicorn handles SIGTERM. |

**Gaps:** No graceful drain for in-flight scheduled batch; shallow `/health` does not gate readiness on DB.

---

## X. Dev/prod parity

**Keep dev and production similar.**

| Status | Evidence |
|--------|----------|
| **Gap** | Local stack: dashboard + app + meilisearch + dev-tools profile. Coolify: db + hasura + gotify (+ optional jupyter profile). Significant parity drift. |

---

## XI. Logs

**Treat logs as event streams.**

| Status | Evidence |
|--------|----------|
| **Partial** | stdout logging; `LOG_LEVEL` env exists. |

**Gaps:** Level not wired; no JSON log format for aggregation; Gotify token may appear in URLs at WARNING+.

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
| X Dev/prod parity | Gap |
| XI Logs | Partial |
| XII Admin processes | Partial |

**Compliance rate:** 3 Compliant + 9 Partial + 0 full Gap on strict reading ≈ **68%** (Partial counts as 0.5).

**Priority fixes:** III (startup secret validation), X (Coolify compose parity), VIII (worker for scheduled ingest), XI (logging wiring).

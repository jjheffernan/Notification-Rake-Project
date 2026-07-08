# Production Readiness Scorecard

Reference rubric for auditing Notification Rake before public deployment. Re-score after each phase in [`PLAN.md`](../../PLAN.md).

**Scoring:** Each category is 0–10. Weighted total → letter grade.

| Grade | Score |
|-------|-------|
| A | 90–100 |
| B | 80–89 |
| C | 70–79 |
| D | 60–69 |
| F | &lt;60 |

---

## Categories

### 1. Deployment & infrastructure (weight 15%)

| Criterion | 10 | 5 | 0 |
|-----------|----|---|--|
| Compose parity | Local + prod stacks match (app, dashboard, meilisearch, db) | Partial stack in prod | Missing core services |
| Secrets | Required env vars enforced; no `change-me` at startup | Documented only | Defaults accepted silently |
| Health checks | Deep `/health` (DB, search, deps) | Shallow liveness | None |
| CI/CD | Lint, test, build, gated deploy webhook | CI only | Manual only |
| Rollback | Documented + one-command revert | Manual steps | None |

**Audit signals:** `deploy/coolify/docker-compose.yml` vs root `docker-compose.yml`, `.github/workflows/ci.yml`, `docs/deploy.md`.

### 2. Authentication & authorization (weight 15%)

| Criterion | 10 | 5 | 0 |
|-----------|----|---|--|
| Public vs operator | Buyer sign-in separate; admin not in public nav | Admin link hidden by default | Admin promoted in nav |
| Buyer identity | Server-validated sessions or signed tokens | Client UUID bearer (current) | No scoping |
| Admin hardening | CSRF, secure cookies, lockout/rate limit | Session only | Plain form, default creds |
| API scoping | All mutating routes require `profile_id` | Most routes | Global batch without profile |
| Credential storage | Encrypted at rest | Plaintext JSON (current) | Logged or exposed |

**Audit signals:** `web/auth.py`, `web/static/rake.js`, `blueprints/public.py`, `metadata.connected_account`.

### 3. Observability (weight 10%)

| Criterion | 10 | 5 | 0 |
|-----------|----|---|--|
| Logging | `LOG_LEVEL` wired; structured JSON in prod | Basic logging | Print/debug only |
| Metrics | Prometheus scrape of app + ingest | Dev profile only | None |
| Tracing | Request IDs / correlation | Partial | None |
| Alerting | Gotify on ingest + job failures | Ingest only | None |
| Admin console | Live dependency health | Static page | None |

**Audit signals:** `admin/console.py`, `deploy/prometheus/`, `config.log_level`.

### 4. Data & persistence (weight 15%)

| Criterion | 10 | 5 | 0 |
|-----------|----|---|--|
| Migrations | Versioned, repeatable (`db/init/`) | Init scripts only | Ad hoc |
| Backups | Automated PG backup + restore drill | Documented manual | None |
| Search | Meilisearch + Postgres fallback | One engine | Broken fallback |
| PII handling | Documented retention + delete path | Implicit | None |
| Job tracking | `metadata.job_run` for batches | Partial | None |

### 5. API & product surface (weight 10%)

| Criterion | 10 | 5 | 0 |
|-----------|----|---|--|
| Rate limiting | Per-IP / per-profile on public API | Admin only | None |
| Caching | Appropriate `Cache-Control` on reads | Some routes | None |
| Error handling | Consistent JSON errors, no stack traces | Mixed | Leaks internals |
| Docs | Wiki + OpenAPI or API reference | Wiki only | Stale |
| Mobile UX | Responsive nav + core flows | Desktop-first | Broken mobile |

### 6. Ingestion & workflow (weight 15%)

| Criterion | 10 | 5 | 0 |
|-----------|----|---|--|
| Source coverage | Craigslist + Yahoo + EU + auctions | Partial | Single source |
| Scheduled searches | Profile-scoped, idempotent runs | Global run gap | Broken |
| Connectors | Env-gated credentials, sync tested | Manual scripts | Untested |
| Idempotency | Upsert keys, dedupe alerts | Mostly | Duplicates |
| Failure recovery | Retry + dead-letter visibility | Log only | Silent fail |

### 7. Testing & quality (weight 10%)

| Criterion | 10 | 5 | 0 |
|-----------|----|---|--|
| Unit tests | Core domain + web routes | Partial | Minimal |
| Integration | DB fixtures in CI | Local only | None |
| Secrets scan | Gitleaks in CI | Pre-commit | None |
| Lint | Ruff clean | Warnings | None |
| E2E | Smoke against compose | Manual | None |

### 8. Documentation & runbooks (weight 10%)

| Criterion | 10 | 5 | 0 |
|-----------|----|---|--|
| Deploy runbook | Coolify + local + secrets | Partial | Missing |
| Security | `SECURITY.md` accurate | Outdated sections | Missing |
| On-call | Incident + rollback steps | Implicit | None |
| Architecture | Current wiki/diagrams | Drift | Absent |
| Plan tracking | `PLAN.md` with phases | Ad hoc issues | None |

---

## How to score

1. Score each category 0–10 using the table anchors.
2. Multiply by weight; sum for **Readiness Score** (0–100).
3. Record evidence (file paths, test results) in `PLAN.md` audit section.
4. Re-audit when a phase closes or before any public launch.

---

## Baseline audit (2026-06-24)

| Category | Score | Notes |
|----------|-------|-------|
| Deployment & infrastructure | 4 | Coolify compose missing dashboard, app, meilisearch |
| Auth & authorization | 5 | Buyer sign-in added; UUID bearer; global batch run |
| Observability | 6 | Admin health probes; `LOG_LEVEL` not wired |
| Data & persistence | 7 | Solid init SQL; no backup automation |
| API & product | 7 | Good caching; no rate limits |
| Ingestion & workflow | 7 | Multi-source; scheduled batch gap |
| Testing & quality | 8 | pytest + gitleaks + ruff |
| Documentation | 6 | Wiki strong; SECURITY.md stale |
| **Weighted total** | **62** | **Grade D** |

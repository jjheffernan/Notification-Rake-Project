# Notification Rake — Deployment & Development Plan

Living roadmap for taking the project from **local MVP** to **public deployment**. Scores are from audits against:

- [`docs/reference/readiness-score.md`](docs/reference/readiness-score.md)
- [`docs/reference/twelve-factor-compliance.md`](docs/reference/twelve-factor-compliance.md)
- [`docs/reference/security-practices.md`](docs/reference/security-practices.md)

**Last audited:** 2026-06-24

---

## Executive summary

| Metric | Score | Grade / status |
|--------|-------|----------------|
| **Production readiness** | 62 / 100 | D — not deployment-ready |
| **12-factor compliance** | ~68% | 3 compliant, 9 partial, 2 gap areas |
| **Security posture** | 47 / 100 | High-risk gaps in authz + credential storage |
| **Composite (avg)** | **59 / 100** | Pre-production |

### Development cycle position

```text
[ Research ] → [ MVP / local ] → [ Hardening ] → [ Staging ] → [ Public launch ]
                    ▲ YOU ARE HERE
```

| Stage | Status |
|-------|--------|
| Core product (search, market, ingest) | ✅ Shipped locally |
| Buyer identity (non-admin sign-in) | ✅ Shipped — `/signin`, nav gated |
| Operator console | ✅ Exists — `/admin`, hidden from public nav |
| Production deploy stack | ❌ Coolify compose incomplete |
| Security hardening | ❌ P0 items open |
| Staging / soak | ⬜ Not started |
| Public launch | ⬜ Blocked on Phases 0–2 |

---

## Audit detail

### Readiness by category

| Category | Wt | Score | Wtd | Evidence |
|----------|-----|-------|-----|----------|
| Deployment & infrastructure | 15% | 4 | 0.60 | `deploy/coolify/docker-compose.yml` missing dashboard, app, meilisearch |
| Auth & authorization | 15% | 5 | 0.75 | Buyer sign-in ✅; UUID bearer; global batch run |
| Observability | 10% | 6 | 0.60 | `admin/console.py` probes; `LOG_LEVEL` unused |
| Data & persistence | 15% | 7 | 1.05 | `db/init/` solid; no automated backups |
| API & product | 10% | 7 | 0.70 | Cache headers ✅; no rate limits |
| Ingestion & workflow | 15% | 7 | 1.05 | Multi-source; `scheduled-searches/run` global gap |
| Testing & quality | 10% | 8 | 0.80 | pytest, ruff, gitleaks CI |
| Documentation | 10% | 6 | 0.60 | Wiki ✅; `SECURITY.md` stale |
| **Total** | | | **62** | |

### 12-factor snapshot

| Factor | Status | Blocker? |
|--------|--------|----------|
| I Codebase | Compliant | |
| II Dependencies | Compliant | |
| III Config | Partial | Startup secret validation |
| IV Backing services | Partial | Coolify missing services |
| V Build/release/run | Partial | Release tagging |
| VI Processes | Partial | Stateless OK; batch in-request |
| VII Port binding | Compliant | |
| VIII Concurrency | Gap | No worker queue |
| IX Disposability | Partial | Shallow health |
| X Dev/prod parity | Gap | **Yes — P0** |
| XI Logs | Partial | LOG_LEVEL wiring |
| XII Admin processes | Partial | One-off scripts exist |

### Security by domain

| Domain | Score | Priority fix |
|--------|-------|--------------|
| Secrets management | 6 | Fail on `change-me` in prod |
| Network exposure | 7 | Full Coolify stack |
| Authentication | 5 | Signed buyer sessions (later) |
| Authorization | 4 | Require `profile_id` on batch run |
| Session/cookies | 5 | Secure + CSRF on admin |
| Data protection | 3 | Encrypt `connected_account.config` |
| Supply chain | 7 | Dependabot |
| Logging | 6 | Wire LOG_LEVEL |
| Incident response | 4 | Runbook |
| Secure development | 5 | Authz API tests |

---

## Point scale (Fibonacci)

Use for sprint planning and sub-agent task sizing.

| Points | Meaning | Typical scope |
|--------|---------|---------------|
| **1** | Trivial | Config flag, copy, single test |
| **2** | Small | One endpoint or template change |
| **3** | Medium | Feature slice with tests |
| **5** | Large | Cross-module vertical slice |
| **8** | Epic | Infra + app + docs |
| **13** | Program | Multi-service, migration, encryption |

---

## Phased rollout (vertical slices)

Each phase is a **deployable increment**. Prefer one **single-purpose sub-agent** per task row.

### Phase 0 — Public surface safety (P0)

**Goal:** Safe to expose dashboard URL publicly (even before full Coolify parity).

| ID | Task | Pts | Sub-agent | Done |
|----|------|-----|-----------|------|
| 0.1 | Buyer sign-in UX; hide Operator from nav (`ADMIN_NAV_VISIBLE=false`) | 3 | `web-auth-nav` | ✅ |
| 0.2 | Gate accounts/watchlist on `requireProfileId()` | 2 | `web-auth-nav` | ✅ |
| 0.3 | Require `profile_id` on `POST /api/scheduled-searches/run` | 2 | `api-authz` | ⬜ |
| 0.4 | Startup validation: reject `change-me` secrets when `RAKE_ENV=production` | 3 | `config-hardening` | ⬜ |
| 0.5 | Update `SECURITY.md` + wiki for buyer vs operator auth | 1 | `docs-security` | ⬜ |
| 0.6 | Authz tests: accounts/watchlist API profile isolation | 3 | `test-authz` | ⬜ |

**Phase exit:** Security authorization ≥6; no global batch without profile.

---

### Phase 1 — Deploy parity (P0)

**Goal:** Coolify stack matches local core services.

| ID | Task | Pts | Sub-agent | Done |
|----|------|-----|-----------|------|
| 1.1 | Add `dashboard`, `app`, `meilisearch` to `deploy/coolify/docker-compose.yml` | 5 | `coolify-compose` | ⬜ |
| 1.2 | Traefik labels for public dashboard only | 3 | `coolify-compose` | ⬜ |
| 1.3 | Document Coolify env matrix in `docs/wiki/Deployment.md` | 2 | `docs-deploy` | ⬜ |
| 1.4 | Deep `/health`: DB + Meilisearch ping | 3 | `health-endpoint` | ⬜ |
| 1.5 | Wire `LOG_LEVEL` to Python logging | 2 | `config-hardening` | ⬜ |
| 1.6 | Staging smoke script (`scripts/ops/smoke_deploy.sh`) | 3 | `ops-smoke` | ⬜ |

**Phase exit:** Readiness deployment score ≥7; 12-factor X (parity) → Partial.

---

### Phase 2 — Credential & admin hardening (P1)

**Goal:** Protect marketplace credentials and operator surface.

| ID | Task | Pts | Sub-agent | Done |
|----|------|-----|-----------|------|
| 2.1 | Encrypt `connected_account.config` at rest (app-level key) | 8 | `credential-encrypt` | ⬜ |
| 2.2 | Strip secrets from API responses | 2 | `credential-encrypt` | ⬜ |
| 2.3 | Admin CSRF + `SESSION_COOKIE_SECURE` in prod | 3 | `admin-session` | ⬜ |
| 2.4 | Rate limit `/api/*` and `/admin/login` | 5 | `api-rate-limit` | ⬜ |
| 2.5 | Dependabot / pip-audit in CI | 2 | `ci-supply-chain` | ⬜ |

**Phase exit:** Security score ≥65; data protection ≥7.

---

### Phase 3 — Background work & scale path (P1)

**Goal:** Scheduled ingest off the request thread.

| ID | Task | Pts | Sub-agent | Done |
|----|------|-----|-----------|------|
| 3.1 | Redis + worker service in compose (dev + coolify) | 8 | `worker-infra` | ⬜ |
| 3.2 | Move `run_scheduled_batch` to worker task | 5 | `worker-scheduled` | ⬜ |
| 3.3 | Cron or Coolify scheduled task for due searches | 3 | `worker-scheduled` | ⬜ |
| 3.4 | Job status UI on watchlist | 3 | `web-watchlist` | ⬜ |

**Phase exit:** 12-factor VIII → Partial; concurrency story documented.

---

### Phase 4 — Operations & launch (P2)

**Goal:** Run production with confidence.

| ID | Task | Pts | Sub-agent | Done |
|----|------|-----|-----------|------|
| 4.1 | PG backup automation + restore doc | 5 | `ops-backup` | ⬜ |
| 4.2 | Incident runbook in `docs/operations/incidents.md` | 3 | `docs-ops` | ⬜ |
| 4.3 | Signed buyer session cookie (optional upgrade from UUID) | 8 | `web-auth-nav` | ⬜ |
| 4.4 | E2E smoke in CI against compose | 5 | `ci-e2e` | ⬜ |
| 4.5 | Release tagging + changelog on deploy | 3 | `ci-release` | ⬜ |

**Phase exit:** Readiness ≥80 (B); composite ≥75.

---

## Sub-agent catalog

Single-purpose agents — assign one task ID per invocation.

| Agent ID | Scope | Inputs |
|----------|-------|--------|
| `web-auth-nav` | Buyer sign-in, nav, `rake.js` profile helpers | `web/templates`, `web/static` |
| `api-authz` | Profile scoping, validation, batch endpoints | `blueprints/public.py` |
| `config-hardening` | `config.py`, startup validators, logging | `config.py`, `web/__init__.py` |
| `coolify-compose` | `deploy/coolify/docker-compose.yml`, Traefik | `docker-compose.yml` reference |
| `health-endpoint` | `/health` depth, readiness vs liveness | `blueprints/public.py` |
| `credential-encrypt` | `storage/accounts.py`, migration SQL | `db/init/` |
| `admin-session` | `web/auth.py`, admin blueprints, cookies | Flask session config |
| `api-rate-limit` | Flask-Limiter or middleware | public + admin blueprints |
| `worker-infra` | Redis, worker Dockerfile target | `docker/` |
| `worker-scheduled` | `workflow/scheduled_batch.py` | worker + API |
| `test-authz` | `tests/test_web.py`, `tests/test_accounts.py` | API routes |
| `docs-security` | `SECURITY.md`, wiki | reference docs |
| `docs-deploy` | `docs/deploy.md`, wiki Deployment | compose files |
| `ops-smoke` | `scripts/ops/` | curl/httpie checks |
| `ci-supply-chain` | `.github/workflows/` | Dependabot config |

---

## Score tracking (update after each phase)

| Date | Readiness | 12-factor | Security | Composite | Notes |
|------|-----------|-----------|----------|-----------|-------|
| 2026-06-24 | 62 | 68% | 47 | 59 | Baseline audit; Phase 0.1–0.2 done |
| | | | | | |
| | | | | | |

---

## Quick links

- Deploy: [`docs/deploy.md`](docs/deploy.md)
- Security checklist: [`SECURITY.md`](SECURITY.md)
- Architecture: [`docs/wiki/Architecture.md`](docs/wiki/Architecture.md)
- Connected accounts: [`docs/wiki/Connected-Accounts.md`](docs/wiki/Connected-Accounts.md)

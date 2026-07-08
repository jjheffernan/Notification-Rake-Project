# Notification Rake — Deployment & Development Plan

Living roadmap for taking the project from **local MVP** to **public deployment**. Scores are from audits against:

- [`docs/reference/readiness-score.md`](docs/reference/readiness-score.md)
- [`docs/reference/twelve-factor-compliance.md`](docs/reference/twelve-factor-compliance.md)
- [`docs/reference/security-practices.md`](docs/reference/security-practices.md)

**Last audited:** 2026-07-08 (post Phase 0–2 merge + post-phase-2 audit)

---

## Executive summary

| Metric | Score | Grade / status |
|--------|-------|----------------|
| **Production readiness** | ~74 / 100 | C — staging-ready; launch needs Phase 3–4 |
| **12-factor compliance** | ~76% | Worker queue still gap (VIII) |
| **Security posture** | ~73 / 100 | Phase 2 exit met (≥65) |
| **Composite (avg)** | **~74 / 100** | Post-audit complete |

### Development cycle position

```text
[ Research ] → [ MVP / local ] → [ Hardening ] → [ Staging ] → [ Public launch ]
                                    ▲ YOU ARE HERE (Phase 3 worker next)
```

| Stage | Status |
|-------|--------|
| Core product (search, market, ingest) | ✅ Shipped locally |
| Buyer identity (non-admin sign-in) | ✅ Shipped — `/signin`, nav gated |
| Operator console | ✅ Exists — `/admin`, hidden from public nav |
| Phase 0 public-surface safety | ✅ Merged — PRs [#1](https://github.com/jjheffernan/Notification-Rake-Project/pull/1)–[#4](https://github.com/jjheffernan/Notification-Rake-Project/pull/4) |
| Production deploy stack | ✅ Phase 1 merged — Coolify compose parity |
| Security hardening (credentials, rate limits) | ✅ Phase 2 merged — PRs [#10](https://github.com/jjheffernan/Notification-Rake-Project/pull/10)–[#13](https://github.com/jjheffernan/Notification-Rake-Project/pull/13) |
| Post–Phase 2 audit | ✅ [`docs/plans/post-phase-2-audit.md`](docs/plans/post-phase-2-audit.md) |
| Staging / soak | ⬜ Manual smoke only |
| Public launch | ⬜ Blocked on Phase 3–4 (readiness ≥80) |

---

## Audit detail

### Readiness by category

| Category | Wt | Score | Wtd | Evidence |
|----------|-----|-------|-----|----------|
| Deployment & infrastructure | 15% | 7 | 1.05 | Coolify compose parity ✅; smoke script; no E2E CI |
| Auth & authorization | 15% | 8 | 1.20 | profile_id batch ✅; encryption ✅; rate limits ✅; UUID bearer |
| Observability | 10% | 6 | 0.60 | `LOG_LEVEL` wired; deep `/health`; no JSON logs |
| Data & persistence | 15% | 6 | 0.90 | `db/init/` solid; encrypted credentials; no backups |
| API & product | 10% | 8 | 0.80 | Rate limits ✅; cache headers; responsive partial |
| Ingestion & workflow | 15% | 8 | 1.20 | Multi-source; profile-scoped batch; in-request worker |
| Testing & quality | 10% | 9 | 0.90 | pytest + ruff + gitleaks + pip-audit + `test_ux_flows.py` |
| Documentation | 10% | 7 | 0.70 | Wiki + audit doc; incident runbook missing |
| **Total** | | | **~74** | Grade C |

### 12-factor snapshot

| Factor | Status | Blocker? |
|--------|--------|----------|
| I Codebase | Compliant | |
| II Dependencies | Compliant | |
| III Config | Partial | `RAKE_ENV` + `LOG_LEVEL` wired ✅ |
| IV Backing services | Partial | No Redis/worker yet |
| V Build/release/run | Partial | Release tagging |
| VI Processes | Partial | Batch in-request |
| VII Port binding | Compliant | |
| VIII Concurrency | Gap | **Yes — Phase 3** |
| IX Disposability | Partial | Deep `/health` ✅ |
| X Dev/prod parity | Partial | Coolify parity ✅ |
| XI Logs | Partial | `LOG_LEVEL` wired |
| XII Admin processes | Partial | One-off scripts exist |

### Security by domain

| Domain | Score | Priority fix |
|--------|-------|--------------|
| Secrets management | 8 | Rotation runbook |
| Network exposure | 8 | Coolify TLS ops |
| Authentication | 6 | Signed buyer sessions (Phase 4) |
| Authorization | 8 | — |
| Session/cookies | 8 | CSRF + secure cookies ✅ |
| Data protection | 8 | Encrypt credentials ✅ |
| Supply chain | 8 | Dependabot + pip-audit ✅ |
| Logging | 7 | Auth failure audit |
| Incident response | 4 | Runbook — Phase 4 |
| Secure development | 8 | `test_ux_flows.py` + authz tests ✅ |

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
| 0.3 | Require `profile_id` on `POST /api/scheduled-searches/run` | 2 | `api-authz` | ✅ [#2](https://github.com/jjheffernan/Notification-Rake-Project/pull/2) |
| 0.4 | Startup validation: reject `change-me` secrets when `RAKE_ENV=production` | 3 | `config-hardening` | ✅ [#1](https://github.com/jjheffernan/Notification-Rake-Project/pull/1) |
| 0.5 | Update `SECURITY.md` + wiki for buyer vs operator auth | 1 | `docs-security` | ✅ [#3](https://github.com/jjheffernan/Notification-Rake-Project/pull/3) |
| 0.6 | Authz tests: accounts/watchlist API profile isolation | 3 | `test-authz` | ✅ [#4](https://github.com/jjheffernan/Notification-Rake-Project/pull/4) |

**Phase exit:** ✅ Met — authorization ≥6; no global batch without profile.

---

### Phase 1 — Deploy parity (P0) ✅ Merged

**Goal:** Coolify stack matches local core services.

| ID | Task | Pts | Sub-agent | Done |
|----|------|-----|-----------|------|
| 1.1 | Add `dashboard`, `app`, `meilisearch` to `deploy/coolify/docker-compose.yml` | 5 | `coolify-compose` | ✅ [#6](https://github.com/jjheffernan/Notification-Rake-Project/pull/6) |
| 1.2 | Traefik labels for public dashboard only | 3 | `coolify-compose` | ✅ [#6](https://github.com/jjheffernan/Notification-Rake-Project/pull/6) |
| 1.3 | Document Coolify env matrix in `docs/wiki/Deployment.md` | 2 | `docs-deploy` | ✅ [#8](https://github.com/jjheffernan/Notification-Rake-Project/pull/8) |
| 1.4 | Deep `/health`: DB + Meilisearch ping | 3 | `health-endpoint` | ✅ [#9](https://github.com/jjheffernan/Notification-Rake-Project/pull/9) |
| 1.5 | Wire `LOG_LEVEL` to Python logging | 2 | `config-hardening` | ✅ [#7](https://github.com/jjheffernan/Notification-Rake-Project/pull/7) |
| 1.6 | Staging smoke script (`scripts/ops/smoke_deploy.sh`) | 3 | `ops-smoke` | ✅ [#5](https://github.com/jjheffernan/Notification-Rake-Project/pull/5) |

**Phase exit:** ✅ Met — deployment parity in compose; deep health + smoke script.

---

### Phase 2 — Credential & admin hardening (P1) ✅ Merged

**Goal:** Protect marketplace credentials and operator surface.

| ID | Task | Pts | Sub-agent | Done |
|----|------|-----|-----------|------|
| 2.1 | Encrypt `connected_account.config` at rest (app-level key) | 8 | `credential-encrypt` | ✅ [#12](https://github.com/jjheffernan/Notification-Rake-Project/pull/12) |
| 2.2 | Strip secrets from API responses | 2 | `credential-encrypt` | ✅ [#12](https://github.com/jjheffernan/Notification-Rake-Project/pull/12) |
| 2.3 | Admin CSRF + `SESSION_COOKIE_SECURE` in prod | 3 | `admin-session` | ✅ [#13](https://github.com/jjheffernan/Notification-Rake-Project/pull/13) |
| 2.4 | Rate limit `/api/*` and `/admin/login` | 5 | `api-rate-limit` | ✅ [#11](https://github.com/jjheffernan/Notification-Rake-Project/pull/11) |
| 2.5 | Dependabot / pip-audit in CI | 2 | `ci-supply-chain` | ✅ [#10](https://github.com/jjheffernan/Notification-Rake-Project/pull/10) |

**Phase exit:** ✅ Met — security 73 (≥65); data protection 8 (≥7).

---

### Post–Phase 2 audit ✅ Complete

| Track | Goal | Sub-agent | Done |
|-------|------|-----------|------|
| Gap audit | Site-wide gaps vs PRD + rubrics | `audit-readiness` | ✅ |
| UX / flow tests | Sign-in → search → watchlist → accounts | `test-ux-flows` | ✅ `tests/test_ux_flows.py` |
| Notifications | Gotify today; email + in-app matrix | `research-notifications` | ✅ |

Deliverable: [`docs/plans/post-phase-2-audit.md`](docs/plans/post-phase-2-audit.md)

---

### Phase 3 — Background work & scale path (P1) ← **NEXT**

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
| `test-authz` | `tests/test_web.py`, `tests/test_accounts.py`, `tests/test_ux_flows.py` | API routes |
| `docs-security` | `SECURITY.md`, wiki | reference docs |
| `docs-deploy` | `docs/deploy.md`, wiki Deployment | compose files |
| `ops-smoke` | `scripts/ops/` | curl/httpie checks |
| `ci-supply-chain` | `.github/workflows/` | Dependabot config |

---

## Score tracking (update after each phase)

| Date | Readiness | 12-factor | Security | Composite | Notes |
|------|-----------|-----------|----------|-----------|-------|
| 2026-06-24 | 62 | 68% | 47 | 59 | Baseline audit; Phase 0.1–0.2 done |
| 2026-07-08 | ~65 | ~70% | ~56 | ~64 | Phase 0 merged (#1–#4); foundation `1fa176e` |
| 2026-07-08 | ~72 | ~75% | ~56 | ~68 | Phase 1 merged (#5–#9) |
| 2026-07-08 | ~74 | ~75% | ~68 | ~72 | Phase 2 swarms done; PRs #10–#13 |
| 2026-07-08 | ~74 | ~76% | ~73 | ~74 | Phase 2 merged; post-audit + rubric re-score |

---

## Quick links

- Deploy: [`docs/deploy.md`](docs/deploy.md)
- Security checklist: [`SECURITY.md`](SECURITY.md)
- Architecture: [`docs/wiki/Architecture.md`](docs/wiki/Architecture.md)
- Connected accounts: [`docs/wiki/Connected-Accounts.md`](docs/wiki/Connected-Accounts.md)

---

## Next actions

**Phase 3 kickoff:** Spawn `worker-infra` (3.1) first, then `worker-scheduled` tasks.

See [`docs/plans/post-phase-2-audit.md`](docs/plans/post-phase-2-audit.md) for gap priorities (worker, backups, per-profile notifications).

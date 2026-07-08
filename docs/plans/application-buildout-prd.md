# PRD: Application build-out to public deployment

**Status:** Phase 0 complete (merged #1–#4). Phase 1 next.

---

## Problem

Notification Rake runs well locally (search, market data, ingest, watchlist, connected accounts) but is **not safe or complete for public hosting**:

- Composite readiness **59/100** (readiness 62, security 47, 12-factor ~68%)
- Coolify production compose missing core services (`dashboard`, `app`, `meilisearch`)
- Buyer auth is client UUID bearer; operator admin exists but must stay off public nav
- Authorization gaps (`scheduled-searches/run` without `profile_id`)
- Marketplace credentials stored plaintext in Postgres

## Goal

Ship a **publicly hostable** vehicle listing platform where:

1. **Buyers** sign in at `/signin`, manage watchlists and connected accounts on their profile
2. **Operators** reach `/admin` directly (not linked from public nav)
3. **Deploy** matches local stack on Coolify with secrets validated at startup
4. **Security** score ≥65 before launch; readiness ≥80 (grade B) at launch

## Non-goals (this PRD)

- Multi-tenant SaaS billing
- Password-based buyer accounts (UUID profile is MVP; signed cookie is Phase 4 optional)
- OpenSearch / Redis scale path beyond Phase 3 worker
- Yahoo proxy quote layer (separate plan: `docs/plans/yahoo-proxy-ingestion.md`)

---

## Users

| Actor | Needs |
|-------|-------|
| **Buyer** | Search listings, market data, save watchlists, connect marketplace accounts, get alerts |
| **Operator** | Stack health, run ingest pipelines, manage sources, view job history |
| **Maintainer** | Deploy to Coolify, rotate secrets, monitor health, triage issues |

---

## Success metrics

| Metric | Current | Phase 0 exit | Launch target |
|--------|---------|--------------|---------------|
| Readiness score | 62 | 68 | ≥80 |
| Security score | 47 | 58 | ≥65 |
| 12-factor compliance | 68% | 75% | ≥85% |
| Coolify compose parity | Partial | N/A | Full core stack |
| Global batch without profile | Yes | No | No |

---

## Phased delivery

Each task is **one sub-agent, one concern**. Points use Fibonacci (see `PLAN.md`).

### Phase 0 — Public surface safety (P0)

| ID | Issue title | Pts | Sub-agent | Acceptance criteria |
|----|-------------|-----|-----------|---------------------|
| 0.3 | Require profile_id on scheduled batch run | 2 | `api-authz` | `POST /api/scheduled-searches/run` returns 400 without `profile_id`; global run removed |
| 0.4 | Reject change-me secrets in production | 3 | `config-hardening` | App fails startup when `RAKE_ENV=production` and placeholder secrets detected |
| 0.5 | Document buyer vs operator auth in wiki | 1 | `docs-security` | Wiki Connected-Accounts + Configuration match `SECURITY.md` |
| 0.6 | Authz tests for profile-scoped APIs | 3 | `test-authz` | Tests prove cross-profile access denied on accounts + watchlist |

**Exit:** Authorization domain score ≥6; no unauthenticated side effects.

### Phase 1 — Deploy parity (P0)

| ID | Issue title | Pts | Sub-agent | Acceptance criteria |
|----|-------------|-----|-----------|---------------------|
| 1.1 | Add dashboard, app, meilisearch to Coolify compose | 5 | `coolify-compose` | `deploy/coolify/docker-compose.yml` mirrors local core services |
| 1.2 | Traefik labels for public dashboard | 3 | `coolify-compose` | Only dashboard public; db/jupyter/adminer internal |
| 1.3 | Document Coolify env matrix | 2 | `docs-deploy` | Wiki Deployment lists every required secret |
| 1.4 | Deep health endpoint | 3 | `health-endpoint` | `/health` checks DB + Meilisearch; returns 503 when degraded |
| 1.5 | Wire LOG_LEVEL to logging | 2 | `config-hardening` | `LOG_LEVEL=DEBUG` increases verbosity |
| 1.6 | Staging smoke script | 3 | `ops-smoke` | `scripts/ops/smoke_deploy.sh` exits 0 against running stack |

**Exit:** Deployment readiness ≥7; dev/prod parity Partial.

### Phase 2 — Credential & admin hardening (P1)

| ID | Issue title | Pts | Sub-agent | Acceptance criteria |
|----|-------------|-----|-----------|---------------------|
| 2.1 | Encrypt connected_account.config at rest | 8 | `credential-encrypt` | Credentials encrypted in DB; migration for existing rows |
| 2.2 | Strip secrets from accounts API JSON | 2 | `credential-encrypt` | API never returns raw passwords/tokens |
| 2.3 | Admin CSRF + secure cookies | 3 | `admin-session` | Production admin session uses Secure + SameSite |
| 2.4 | Rate limit public API and admin login | 5 | `api-rate-limit` | 429 after threshold; admin brute-force slowed |
| 2.5 | Dependabot in CI | 2 | `ci-supply-chain` | `.github/dependabot.yml` + optional pip-audit job |

**Exit:** Security ≥65; data protection ≥7.

### Phase 3 — Background work (P1)

| ID | Issue title | Pts | Sub-agent | Acceptance criteria |
|----|-------------|-----|-----------|---------------------|
| 3.1 | Redis + worker in compose | 8 | `worker-infra` | Worker service in local + Coolify compose |
| 3.2 | Move scheduled batch to worker | 5 | `worker-scheduled` | API enqueues; worker executes |
| 3.3 | Cron for due scheduled searches | 3 | `worker-scheduled` | Due searches run without manual click |
| 3.4 | Job status on watchlist UI | 3 | `web-watchlist` | Last run + outcome visible per search |

**Exit:** 12-factor VIII → Partial.

### Phase 4 — Operations & launch (P2)

| ID | Issue title | Pts | Sub-agent | Acceptance criteria |
|----|-------------|-----|-----------|---------------------|
| 4.1 | PG backup automation | 5 | `ops-backup` | Documented backup + tested restore |
| 4.2 | Incident runbook | 3 | `docs-ops` | `docs/operations/incidents.md` |
| 4.3 | Signed buyer session cookie (optional) | 8 | `web-auth-nav` | Server-bound profile; UUID restore still works |
| 4.4 | E2E smoke in CI | 5 | `ci-e2e` | Compose up + HTTP checks in GitHub Actions |
| 4.5 | Release tagging on deploy | 3 | `ci-release` | Deploy webhook tags image version |

**Exit:** Readiness ≥80 (B); public launch approved.

---

## Sub-agent invocation pattern

One agent per task ID. Prompt template:

```text
Task: PLAN.md Phase <N> task <ID>
Sub-agent: <agent-id>
Scope: <single file or module from PLAN.md>
Done when: <acceptance criteria from this PRD>
Do not touch: <adjacent concerns>
```

Example:

```text
Task: PLAN.md Phase 0 task 0.3
Sub-agent: api-authz
Scope: POST /api/scheduled-searches/run in blueprints/public.py
Done when: 400 without profile_id; tests pass
Do not touch: buyer sign-in UI, Coolify compose
```

---

## Open decisions

| Decision | Default | Revisit when |
|----------|---------|--------------|
| Buyer auth model | UUID in localStorage | Phase 4 if abuse observed |
| `RAKE_ENV` vs inferring prod from secrets | Add `RAKE_ENV=production` | Phase 0.4 |
| Worker tech | Redis + simple Python worker | Phase 3.1 |
| Public market data without sign-in | Yes (current) | Never block search/market |

---

## Issue creation (next step)

Phase 0 complete. Run `/to-issues` on **Phase 1** section below, or:

```bash
gh issue create --title "Phase 1.1: Add dashboard, app, meilisearch to Coolify compose" \
  --label "ready-for-agent" \
  --body "See docs/plans/application-buildout-prd.md Phase 1 task 1.1 and PLAN.md"
```

---

## Related docs

- [`PLAN.md`](../../PLAN.md) — live scoreboard + phase checkboxes
- [`docs/reference/readiness-score.md`](../reference/readiness-score.md)
- [`docs/reference/security-practices.md`](../reference/security-practices.md)
- [`docs/plans/split-to-prs-draft.md`](split-to-prs-draft.md) — split current dirty tree

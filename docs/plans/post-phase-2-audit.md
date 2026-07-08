# Post–Phase 2 audit

**Date:** 2026-07-08  
Living notes from post-Phase 2 audit swarms (gap analysis, UX tests, notifications).

**Scope:** Phases 0–2 merged on `main`. Evidence from code + compose + CI, compared to `docs/plans/application-buildout-prd.md`, `docs/reference/readiness-score.md`, `docs/reference/twelve-factor-compliance.md`, `docs/reference/security-practices.md`, and `PLAN.md`.

**Scores (from `PLAN.md`, not re-scored here):** readiness ~74, security ~68, 12-factor ~75%, composite ~72. Launch targets: readiness ≥80, security ≥65, 12-factor ≥85%.

---

## Gap audit

### Executive summary — top 5 blockers for staging / public

1. **No background worker or cron for watchlist batches (Phase 3)** — Due searches only run when a buyer clicks “Run due” or an operator triggers admin/cron script; `run_scheduled_batch` still executes inside the HTTP request (`src/notification_rake/web/blueprints/public.py`, `workflow/scheduled_batch.py`). No Redis/worker in `docker-compose.yml` or `deploy/coolify/docker-compose.yml`.
2. **No staging gate or E2E smoke in CI (Phase 1.6 partial, 4.4)** — `scripts/ops/smoke_deploy.sh` exists but is not invoked from `.github/workflows/ci.yml`; `deploy` job fires Coolify webhook on `main` push without a compose smoke pass.
3. **No PG backup automation or incident runbook (Phase 4.1–4.2)** — No `docs/operations/incidents.md`; no backup/restore scripts or docs beyond rubric placeholders (`docs/reference/readiness-score.md` §4, §8).
4. **Buyer watchlist alerts are operator-global, not per-profile** — All alerts go through one `GOTIFY_TOKEN` (`src/notification_rake/notifications/alerts.py`, `integrations/gotify.py`); no profile→channel mapping. Multi-buyer public hosting cannot deliver personal alerts.
5. **Coolify ingress wider than PRD/security bar** — `hasura` and `gotify` have `traefik.enable=true` in `deploy/coolify/docker-compose.yml`; security reference expects least-privilege (dashboard + required APIs only). Hasura console + Gotify UI enlarge attack surface on a public host.

**Secondary (not top-5 but actionable):** stale operator docs (`SECURITY.md`, `docs/wiki/Deployment.md` still describe pre–Phase 1/2 state); `pip-audit` allowed to fail in CI (`continue-on-error: true`); in-memory rate limits not shared across gunicorn workers (`src/notification_rake/web/rate_limit.py`); composite/readiness still below launch grade B.

---

### Gap table

| Gap | Severity | Phase / task | Evidence |
|-----|----------|--------------|----------|
| Scheduled batch runs in-request; no worker queue | **P0** | 3.1, 3.2 | `src/notification_rake/web/blueprints/public.py` (`POST /api/scheduled-searches/run`), `src/notification_rake/workflow/scheduled_batch.py`, no `redis`/`worker` in `docker-compose.yml`, `deploy/coolify/docker-compose.yml` |
| No cron / Coolify scheduled task for due searches | **P0** | 3.3 | `scripts/ops/run_scheduled_searches.py` (CLI only), no `cron`/`schedule` in compose files |
| Smoke script not wired into CI; deploy not gated | **P0** | 1.6, 4.4 | `scripts/ops/smoke_deploy.sh`, `.github/workflows/ci.yml` (no smoke step; `deploy` webhook only) |
| No PG backup + tested restore | **P0** | 4.1 | No backup scripts under `scripts/ops/`; rubric gap in `docs/reference/readiness-score.md` |
| No incident / rollback runbook | **P1** | 4.2 | `docs/operations/` absent; `docs/reference/security-practices.md` §9 |
| Per-buyer alerts undefined (global Gotify) | **P0** | PRD §Users (alerts) | `src/notification_rake/notifications/alerts.py`, `src/notification_rake/integrations/gotify.py` |
| Hasura + Gotify public on Traefik | **P1** | 1.2 / security §2 | `deploy/coolify/docker-compose.yml` (`hasura`, `gotify` labels) vs `docs/reference/security-practices.md` |
| Buyer identity is client UUID bearer (no server session) | **P1** | 4.3 (optional) | `src/notification_rake/web/static/rake.js`, `POST /api/profile` in `public.py` (generates UUID only) |
| Rate limits process-local (weak under `--workers 2`) | **P2** | 2.4 follow-up | `src/notification_rake/web/rate_limit.py` (`ponytail:` comment) |
| `pip-audit` non-blocking in CI | **P2** | 2.5 | `.github/workflows/ci.yml` `supply-chain` job `continue-on-error: true` |
| No immutable release tagging on deploy | **P2** | 4.5, 12-factor V | `.github/workflows/ci.yml` `deploy` job (webhook only) |
| Structured JSON logs not implemented | **P2** | 12-factor XI | `src/notification_rake/config.py` `configure_logging()` (level only) |
| `SECURITY.md` stale (pre–Phase 0/2 claims) | **P2** | 0.5 follow-up | `SECURITY.md` lines 38–40 |
| `docs/wiki/Deployment.md` stale (compose parity, env matrix) | **P2** | 1.3 follow-up | `docs/wiki/Deployment.md` § “Not yet in compose” vs `deploy/coolify/docker-compose.yml` |
| `CREDENTIAL_ENCRYPTION_KEY` not in Coolify dashboard `environment:` block | **P2** | 2.1 ops | `deploy/coolify/docker-compose.yml` `dashboard` service (relies on `env_file` only) |
| Readiness composite below launch target (~74 vs ≥80) | **P1** | 4 exit | `PLAN.md`, `docs/plans/application-buildout-prd.md` success metrics |
| 12-factor compliance ~75% vs launch ≥85% | **P1** | VIII, X, XI | `docs/reference/twelve-factor-compliance.md`, worker + parity gaps above |
| Prometheus / metrics not in prod compose | **P2** | readiness §3 | `docker-compose.yml` `prometheus` profile `dev-tools` only |
| No OpenAPI / API reference | **P3** | readiness §5 | Wiki only per rubric |
| PII retention / delete path undocumented | **P2** | readiness §4 | No policy doc under `docs/` |

---

### Undefined / broken user flows

| Flow | Status | Evidence |
|------|--------|----------|
| **Sign in → search (no auth)** | OK | Search/market pages do not call `requireProfileId()` (`src/notification_rake/web/static/rake.js` only used on accounts/watchlist) |
| **Sign in → watchlist → auto alerts** | **Broken / undefined** | No cron/worker; alerts require manual “Run due” or operator script. Alerts fan out to global Gotify, not the signed-in buyer |
| **Sign in → connected account → sync** | Partial | API + UI exist (`accounts.js`, `POST /api/accounts/sync`); **no delete/disconnect in UI** though `DELETE /api/accounts/<id>` exists in `public.py` |
| **Restore profile UUID** | **Undefined** | Client accepts any valid UUID (`signin.js`, `rake.js`); server never checks profile exists — empty accounts/watchlist with no error |
| **Lose localStorage UUID** | **Data loss** | No server-side profile registry (`new_profile_id()` in `storage/accounts.py`); watchlist/accounts keyed only by client-held UUID |
| **Long “Run all” on watchlist** | **Risk** | Synchronous ingest + search in request (`scheduled_batch.py`); proxy/load balancer timeout likely on large route sets |
| **Operator scheduled batch** | Intentional global | Admin action `run_scheduled_searches` runs all profiles (`src/notification_rake/admin/console.py`); distinct from public API scoping |
| **Watchlist job outcome per search** | Partial | UI shows `last_run_at` / match counts (`watchlist.js`); Phase 3.4 “outcome” / `metadata.job_run` not surfaced to buyers |

---

### PRD requirements not yet met

**Launch success metrics (`application-buildout-prd.md`):**

| Metric | Target | Current (PLAN.md) | Met? |
|--------|--------|-------------------|------|
| Readiness score | ≥80 | ~74 | No |
| Security score | ≥65 | ~68 | Yes |
| 12-factor compliance | ≥85% | ~75% | No |
| Coolify compose parity | Full core stack | dashboard, app, meilisearch present | Yes |
| Global batch without profile (public API) | No | `profile_id` required on `POST /api/scheduled-searches/run` | Yes |

**Phase 3 — Background work (all open):**

| ID | Requirement | Status |
|----|-------------|--------|
| 3.1 | Redis + worker in local + Coolify compose | Not started |
| 3.2 | API enqueues; worker executes `run_scheduled_batch` | Not started |
| 3.3 | Cron for due scheduled searches | Not started |
| 3.4 | Job status (last run + outcome) on watchlist UI | Partial — timestamps only |

**Phase 4 — Operations & launch (all open):**

| ID | Requirement | Status |
|----|-------------|--------|
| 4.1 | PG backup automation + tested restore | Not started |
| 4.2 | `docs/operations/incidents.md` | Not started |
| 4.3 | Signed buyer session cookie (optional) | Not started |
| 4.4 | E2E smoke in CI against compose | Not started |
| 4.5 | Release tagging on deploy | Not started |

**PRD user needs still incomplete:**

| Actor | Unmet need |
|-------|------------|
| **Buyer** | Personal alerts (not global Gotify); automatic due-search runs without manual click |
| **Operator** | Documented incident/rollback; backup restore drill |
| **Maintainer** | CI-gated deploy; staging soak; accurate SECURITY/Deployment docs |

**Phases 0–2 — verified merged (spot-check):**

| ID | Acceptance | Evidence |
|----|------------|----------|
| 0.3 | `profile_id` on batch run | `public.py` `api_run_scheduled_searches`, `tests/test_scheduled_searches.py` |
| 0.4 | Reject `change-me` in production | `config.py` `_reject_production_placeholders` |
| 0.6 | Authz tests | `tests/test_accounts.py`, `tests/test_scheduled_searches.py` |
| 1.1–1.2 | Coolify core stack + Traefik on dashboard | `deploy/coolify/docker-compose.yml` |
| 1.4 | Deep `/health` | `public.py` `health()`, `tests/test_web.py` |
| 1.5 | `LOG_LEVEL` wired | `config.py` `configure_logging()`, `web/__init__.py` |
| 1.6 | Smoke script | `scripts/ops/smoke_deploy.sh` (manual only) |
| 2.1–2.2 | Encrypt + mask credentials | `storage/credential_crypto.py`, `storage/accounts.py`, `tests/test_accounts.py` |
| 2.3 | Admin CSRF + secure cookies | `web/auth.py`, `web/__init__.py`, `tests/test_web.py` |
| 2.4 | Rate limits | `web/rate_limit.py`, `tests/test_rate_limit.py` |
| 2.5 | Dependabot + pip-audit | `.github/dependabot.yml`, `.github/workflows/ci.yml` |

**Recommended next actions:** Phase 3.1 worker-infra → 3.2–3.3 cron; Phase 4.4 CI smoke gate; docs janitor for `SECURITY.md` / `Deployment.md`; per-profile notifications (see below).

---

## UX flow tests

Integration coverage for the Phase 0–2 buyer journey lives in `tests/test_ux_flows.py` (Flask test client + pytest, no new dependencies).

| Flow | API / page | Tests |
|------|------------|-------|
| Sign-in | `GET /signin`, `POST /api/profile` | Profile creation returns valid UUID; restore path UI present; existing UUID accepted by profile-scoped APIs; invalid UUID rejected |
| Vehicle search | `GET /api/listings`, `GET /m` | Search returns results; query filters forwarded to `search_listings`; market index page loads |
| Watchlist | `GET /watchlist`, `GET/POST/DELETE /api/scheduled-searches` | Add → list → remove with `profile_id`; cross-profile delete returns 404 |
| Connected accounts | `GET /accounts`, `GET/POST/DELETE /api/accounts` | Connect → list (masked secrets) → disconnect; other profile sees empty list |
| End-to-end | Chained above | `test_buyer_journey_signin_search_watchlist_accounts` exercises full flow in one session |
| Public nav | `/`, `/signin`, `/watchlist`, `/accounts`, `/m` | Operator/admin links hidden from buyer pages |

**Not covered (client-side only):**

- `localStorage` (`rake_profile_id`) read/write — browser-only; server tests use `profile_id` query/body params instead.
- Sign-in redirect when already signed in (`signin.js` `redirectIfSignedIn`) — requires JS runtime.
- `/market` route — app serves market at `/m` (no `/market` alias).

**Run:**

```bash
pytest tests/test_ux_flows.py -v
```

---

## Notifications research

**Sources:** `src/notification_rake/notifications/alerts.py`, `src/notification_rake/integrations/gotify.py`, `src/notification_rake/workflow/{pipeline,routes,scheduled_batch}.py`, `src/notification_rake/web/blueprints/public.py`, `db/init/005_saved_search.sql`, `db/init/010_scheduled_search.sql`, `tests/test_gotify.py`, `tests/test_alerts.py`, `docs/plans/application-buildout-prd.md`.

### 1. Current state

#### Architecture

All outbound alerts today flow through a **single global Gotify app token**. There is no per-buyer routing, no notification persistence, and no email stack.

```text
Trigger (ingest or watchlist)
  → notify_new_listings()          # notifications/alerts.py
    → format_listing_message()     # title · price · year · make model
    → send_alert()                 # integrations/gotify.py
      → POST {GOTIFY_URL}/message?token={GOTIFY_TOKEN}
      → no-op if GOTIFY_TOKEN unset
```

Gotify is also probed for **operator health** in `admin/console.py` (`GET {GOTIFY_URL}/`). `GOTIFY_PUBLIC_URL` is an admin dashboard link only — not used when sending alerts.

#### Config / env vars

| Variable | Default | Role |
|----------|---------|------|
| `GOTIFY_URL` | `http://gotify:80` | Internal push API base (Docker service name) |
| `GOTIFY_TOKEN` | *(empty)* | App token; **required non-empty when `RAKE_ENV=production`** (`config.py` validator) |
| `GOTIFY_PUBLIC_URL` | `http://127.0.0.1:8081` | Browser link on admin health page |
| `GOTIFY_ADMIN_PASS` | — | Gotify container first-login password (compose only; not read by app) |

No SMTP, webhook, or per-profile notification env vars exist.

#### Buyer identity (relevant for routing)

- Profiles are **UUIDs only** — `POST /api/profile` returns `new_profile_id()`; no `metadata.profile` table.
- Profile ID lives in browser `localStorage` (`rake_profile_id`). No email, phone, or server-side contact field.
- Watchlist rows are scoped by `metadata.saved_search.profile_id`.

#### Triggers (what actually fires Gotify today)

| Trigger | Entry point | `notify` default | Notes |
|---------|-------------|------------------|-------|
| **Craigslist pipeline** | `workflow/pipeline.py` → `run_pipeline()` / `sync()` | `True` | One Gotify message **per new upsert** |
| **Per-route ingest** | `workflow/routes.py` → `run_route()` / `sync_route_listings()` | `True` | Copart, Yahoo, EU, Cars & Bids, Craigslist, etc. |
| **Multi-route batch** | `workflow/routes.py` → `run_all_routes()` | `True` | Aggregates per-route `alerted` counts |
| **Scheduled watchlist match** | `workflow/scheduled_batch.py` → `run_single_scheduled_search()` | N/A | Calls `notify_new_listings()` when `alert_enabled` and **new IDs vs `last_seen_ids`**; **skips first run** (`prev` empty); caps at **20** listings per run |
| **Route refresh inside batch** | `scheduled_batch._refresh_routes()` | `False` | Ingest refresh does not alert — only search delta does |
| **Connected-account sync** | `workflow/multi_source.py` → `run_connected_sync()` | `False` | Explicitly disabled |
| **Cron due searches** | `scripts/ops/run_scheduled_searches.py` | N/A | `run_scheduled_batch()` with no `profile_id` — all due searches cluster-wide |
| **Manual watchlist run** | `POST /api/scheduled-searches/run` | N/A | Requires `profile_id`; same batch logic |

**Not implemented:** job failure alerts, admin login anomalies, connected-account errors, auction-ending / price-drop (see `docs/plans/copart-auction-ingestion.md` — planned only).

#### UI / API surface

- Watchlist form (`watchlist.html`): checkbox **"Gotify alert on new matches"** → `alert_enabled` on `metadata.saved_search` (default `true` on create).
- Batch run response exposes `total_alerted` and per-search `alerted` counts — no notification history.
- `metadata.job_runs.alerted` records aggregate counts for operator jobs; not buyer-visible.

#### Tests documenting Gotify behavior

- `tests/test_gotify.py` — `send_alert` no-ops without token; posts JSON `{title, message, priority}` with token query param.
- `tests/test_alerts.py` — `notify_new_listings` calls `send_alert` once per listing; `format_listing_message` shape.

#### Known gaps

1. **Global fan-out** — every buyer watchlist alert hits the operator's Gotify, not the buyer who owns the search.
2. **No dedupe across channels** — re-upsert of same listing can alert again on ingest paths (upsert `is_new` is the guard).
3. **No failure notifications** — `finish_job(..., status="failed")` does not call Gotify.
4. **First-run silence** — watchlist baseline run never alerts (by design); buyers may not understand why.

---

### 2. Event matrix (Gotify today → proposed email + in-app)

| Event | Gotify today | Email (proposed) | In-app (proposed) | Priority |
|-------|--------------|------------------|-------------------|----------|
| New listing on **ingest pipeline** (operator-driven) | ✅ Per listing, global token | ❌ | ❌ | **P2** — keep Gotify for ops; email noise |
| New listing on **route ingest** (admin console) | ✅ Same | ❌ | ❌ | **P2** — operator channel only |
| **Watchlist: new matches** (scheduled / manual batch) | ✅ Global Gotify (wrong audience) | ✅ Digest to buyer opt-in email | ✅ Per-profile unread rows | **P0** — core buyer value |
| **Watchlist: first-run baseline** | ❌ (skipped) | ❌ | ✅ Optional "search armed" ack | **P3** |
| **Job / batch failure** (ingest or scheduled) | ❌ | ❌ | ✅ Operator banner + row | **P1** — ops visibility |
| **Connected account sync** success/fail | ❌ | ❌ | ✅ Profile-scoped status | **P2** |
| **Auction ending / bid drop** (Copart phase 3) | ❌ (planned) | ✅ Optional digest | ✅ Real-time badge | **P3** — after Copart live poll |
| **Admin login failure spike** | ❌ | ❌ | ❌ (logs only) | **P4** — defer |
| **Rate-limit / API abuse** | ❌ | ❌ | ❌ | **P4** — defer |

**Channel roles (proposed):**

- **Gotify** — operator / maintainer: ingest volume, stack failures, deploy smoke. Not buyer-facing.
- **Email** — buyer opt-in digests for watchlist matches (and later auction urgency). Low frequency, batched.
- **In-app** — buyer primary channel: unread notifications tied to `profile_id`, visible on watchlist/profile UI.

---

### 3. Minimal implementation recommendation (Phase 3 / 4)

No new dependencies. Extend existing modules; reuse Postgres + stdlib.

#### Phase 3 — wire channels before scale (fits existing PRD tasks)

| Task | Scope | Points |
|------|-------|--------|
| **3.5** Notification dispatch seam | Add `notifications/dispatch.py`: `dispatch(event, profile_id?, payload) -> None` fans out to registered channels. Refactor `notify_new_listings` to build a `ListingMatchEvent` and call dispatch. Keep `gotify.send_alert` as `OperatorChannel`. | 3 |
| **3.6** In-app store + API | Migration: `metadata.notification (id, profile_id, kind, title, body, link, read_at, created_at)`. Insert on watchlist match. `GET /api/notifications?profile_id=` + `POST .../read`. Badge on nav. **Delivers 3.4 UI hook** (last run + unread count). | 5 |
| **3.7** Route watchlist alerts to profile | In `scheduled_batch`, pass `search.profile_id` into dispatch; **stop sending buyer match alerts to global Gotify** (operator ingest alerts unchanged). | 2 |
| *(existing)* **3.2–3.3** Worker + cron | Notifications fire from worker process — same dispatch code, no new queue lib beyond Redis already planned. | — |

#### Phase 4 — email when identity allows

| Task | Scope | Points |
|------|-------|--------|
| **4.6** Profile contact + opt-in | `metadata.profile (id UUID PK, contact_email, email_opt_in, created_at)` or add columns via migration; `PATCH /api/profile` with validation. Email only when `email_opt_in` and address verified (double opt-in link stored as token). | 5 |
| **4.7** SMTP via stdlib | `integrations/email.py` using `smtplib` + env `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. **Digest only:** one email per watchlist run with ≤20 matches, not per listing. | 3 |
| *(optional)* **4.3** Signed session | Makes in-app + email preferences harder to spoof; UUID restore still works. | 8 |

#### Explicit non-goals (ponytail)

- No SendGrid/Mailgun SDK — stdlib SMTP or platform relay (Coolify/SES SMTP) only.
- No WebPush / FCM until buyer auth is stronger than UUID-in-localStorage.
- No real-time email per listing — digest per batch run.
- No Celery/RQ beyond Phase 3 Redis worker already planned.

#### Suggested dispatch shape (sketch)

```python
# notifications/dispatch.py — one fan-out, three thin channels
def dispatch_watchlist_matches(profile_id: str, search_name: str, listings: list[VehicleListing]) -> None:
    payload = {...}
    in_app.insert(profile_id, payload)
    if profile.email_opt_in:
        email.send_digest(profile.contact_email, payload)  # batched
    # gotify: only if profile_id is None (operator ingest path)
```

---

### 4. Security / privacy notes (email)

| Topic | Guidance |
|-------|----------|
| **Opt-in** | No email without explicit `email_opt_in` + confirmed address. Default off. Watchlist `alert_enabled` should gate in-app; email is a separate toggle. |
| **Data minimization** | Email body: search name, match count, links to `/` with query params — avoid full seller/location PII in subject lines. |
| **Profile recovery** | Today profile ID is the only credential. Email verification must not replace UUID recovery without signed session (Phase 4.3). |
| **Secrets** | SMTP creds in env only; never return from API; production validator like `gotify_token`. |
| **Logging** | Do not log email bodies, tokens, or SMTP auth. Keep `LOG_LEVEL=WARNING` in prod (Gotify token already in URL query — same class of leak). |
| **Rate limiting** | Cap digests per profile per hour (reuse `api_rate_limit` pattern or DB `last_email_at`). Prevents abuse if profile ID leaks. |
| **Unsubscribe** | One-click link sets `email_opt_in=false` for that profile (signed token, no login required). |
| **Cross-profile** | All notification queries must filter `profile_id` — same bar as `scheduled-searches` authz tests. |
| **Transport** | Document TLS requirement for `SMTP_PORT=587`; prefer platform relay with SPF/DKIM managed by host. |
| **Retention** | In-app rows: 90-day TTL or cap 500 per profile (ponytail: periodic delete in worker). |

---

### Summary

Notifications are **Gotify-only, global, and operator-centric**. Buyer watchlist alerts technically work but deliver to the maintainer's push token, not the buyer. The smallest path to real buyer notifications is **in-app rows scoped to `profile_id` (Phase 3)**, then **opt-in SMTP digests (Phase 4)** once a contact field exists. Keep Gotify for operator ingest/failure signal; route watchlist matches away from global Gotify.

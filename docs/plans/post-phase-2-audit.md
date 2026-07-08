# Post-Phase 2 audit

Living notes from post-Phase 2 audit swarms (gap analysis, UX tests, notifications). Each swarm appends a section below.

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

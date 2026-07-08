# Security Practices Reference

Baseline expectations for publicly hosted Notification Rake. Use with [`SECURITY.md`](../../SECURITY.md) and re-score in [`PLAN.md`](../../PLAN.md).

**Scoring:** 10 domains × 0–10 → **Security Score** (0–100).

**Last audited:** 2026-07-08 (post Phase 0–2 merge)

---

## 1. Secrets management

| Practice | Required |
|----------|----------|
| No secrets in Git | Gitleaks CI + `.gitignore` for `.env` |
| Strong random production values | All `change-me` replaced |
| Startup rejection of defaults | Fail fast when `RAKE_ENV=production` |
| Secret rotation runbook | Documented owner + cadence |

**Current:** Gitleaks in CI ✅. `RAKE_ENV=production` rejects placeholders ✅. Rotation runbook partial ⚠️.

---

## 2. Network exposure

| Practice | Required |
|----------|----------|
| DB not public | Bind localhost / internal network only |
| Admin tools off Traefik | Jupyter, Adminer, Metabase dev-profile or internal |
| TLS termination | Traefik / reverse proxy with HTTPS |
| Least-privilege ingress | Only dashboard + required APIs public |

**Current:** Local compose binds `127.0.0.1` ✅. Coolify compose includes `dashboard`, `app`, `meilisearch` internal; Traefik on dashboard/hasura/gotify ✅.

---

## 3. Authentication

| Actor | Model | Production bar |
|-------|-------|----------------|
| **Buyer** | Profile UUID in `localStorage` | Acceptable for MVP if API scoped; prefer signed session cookie |
| **Operator** | `/admin/login` form session | Strong password, not linked from public nav, optional IP allowlist |
| **Service** | Env tokens (Gotify, Hasura, Meilisearch) | Scoped tokens, never in client JS |

**Current:**
- `ADMIN_NAV_VISIBLE=false` default ✅
- Buyer must visit `/signin` before accounts/watchlist ✅
- Admin CSRF + rate-limited login ✅
- `profile_id` is a bearer token — anyone with UUID can act as that profile ⚠️

---

## 4. Authorization & API safety

| Practice | Required |
|----------|----------|
| Profile scoping | All CRUD on accounts, watchlist, scheduled searches |
| No global side effects | Batch ingest/run must require `profile_id` or admin |
| Input validation | UUID format, bounds on limits |
| Rate limiting | Per-IP on `/api/*` and auth endpoints |

**Current:** `_validate_profile_id` on routes ✅. `POST /api/scheduled-searches/run` requires `profile_id` ✅. Per-IP rate limits ✅ (`web/rate_limit.py`).

---

## 5. Session & cookie security

| Practice | Required |
|----------|----------|
| `SECRET_KEY` strong random | `DASHBOARD_SECRET_KEY` |
| `HttpOnly`, `Secure`, `SameSite` | On admin session cookie in prod |
| Session fixation | Regenerate session on login |

**Current:** Flask signed cookie for admin ✅. Production `SESSION_COOKIE_SECURE` + `HttpOnly` + `SameSite=Lax` ✅. CSRF on login ✅.

---

## 6. Data protection

| Data | Risk | Mitigation |
|------|------|------------|
| Marketplace credentials in `connected_account.config` | High | Encrypt at rest (KMS or app-level); never return secrets in API JSON |
| Listing PII | Medium | Minimize storage; retention policy |
| API usage logs | Low | No tokens in query strings logged at INFO |

**Current:** Fernet encryption at rest ✅ (`storage/credential_crypto.py`). API masks secrets ✅. Retention policy not documented ⚠️.

---

## 7. Dependency & supply chain

| Practice | Required |
|----------|----------|
| Pinned image tags | Docker compose |
| CI on every PR | pytest + ruff + gitleaks |
| Dependency updates | Periodic pip-audit or Dependabot |

**Current:** Pinned images ✅. CI ✅. Dependabot + pip-audit job ✅.

---

## 8. Logging & monitoring

| Practice | Required |
|----------|----------|
| No secrets in logs | Redact tokens |
| Failed auth logging | Admin login failures |
| Anomaly detection | Optional — rate limit alerts |

**Current:** `LOG_LEVEL` wired ✅. Gotify token in URL — keep `WARNING` in prod documented ✅. No structured auth-failure audit ⚠️.

---

## 9. Incident response

| Practice | Required |
|----------|----------|
| Contact / owner | In SECURITY.md |
| Revocation steps | Rotate secrets, invalidate sessions |
| Backup restore | PG restore tested |

**Current:** Partial documentation ⚠️. No `docs/operations/incidents.md` ❌.

---

## 10. Secure development

| Practice | Required |
|----------|----------|
| Threat model for new features | Profile in PR template or PLAN |
| Security tests | Authz tests for API routes |
| Pre-deploy checklist | SECURITY.md production table |

**Current:** `tests/test_accounts.py`, `tests/test_web.py`, `tests/test_ux_flows.py` ✅.

---

## Audit (2026-07-08, post Phase 0–2)

| Domain | Score | Top gap |
|--------|-------|---------|
| Secrets management | 8 | Rotation runbook |
| Network exposure | 8 | TLS/ingress ops on Coolify |
| Authentication | 6 | UUID bearer |
| Authorization | 8 | — |
| Session/cookies | 8 | — |
| Data protection | 8 | PII retention policy |
| Supply chain | 8 | — |
| Logging | 7 | Auth failure audit |
| Incident response | 4 | No runbook |
| Secure development | 8 | — |
| **Total** | **73** | |

---

## Hardening priority (P0 → P2)

1. **P0 (done):** `profile_id` on scheduled batch; encrypt connected-account config; startup secret validation; rate limits; admin CSRF/cookies.
2. **P1:** Worker queue; deep health ✅; Coolify full stack ✅; staging E2E.
3. **P2:** Signed buyer sessions; backup automation; incident runbook; IP allowlist for `/admin`.

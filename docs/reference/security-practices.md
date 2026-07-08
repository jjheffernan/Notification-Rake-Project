# Security Practices Reference

Baseline expectations for publicly hosted Notification Rake. Use with [`SECURITY.md`](../../SECURITY.md) and re-score in [`PLAN.md`](../../PLAN.md).

**Scoring:** 10 domains × 0–10 → **Security Score** (0–100).

---

## 1. Secrets management

| Practice | Required |
|----------|----------|
| No secrets in Git | Gitleaks CI + `.gitignore` for `.env` |
| Strong random production values | All `change-me` replaced |
| Startup rejection of defaults | Fail fast when `ENV=production` |
| Secret rotation runbook | Documented owner + cadence |

**Current:** Gitleaks in CI ✅. Defaults still accepted at runtime ⚠️.

---

## 2. Network exposure

| Practice | Required |
|----------|----------|
| DB not public | Bind localhost / internal network only |
| Admin tools off Traefik | Jupyter, Adminer, Metabase dev-profile or internal |
| TLS termination | Traefik / reverse proxy with HTTPS |
| Least-privilege ingress | Only dashboard + required APIs public |

**Current:** Local compose binds `127.0.0.1` ✅. Coolify Traefik for Hasura/Gotify documented ✅. Dashboard not yet in Coolify compose ⚠️.

---

## 3. Authentication

| Actor | Model | Production bar |
|-------|-------|----------------|
| **Buyer** | Profile UUID in `localStorage` | Acceptable for MVP if API scoped; prefer signed session cookie |
| **Operator** | `/admin/login` form session | Strong password, not linked from public nav, optional IP allowlist |
| **Service** | Env tokens (Gotify, Hasura, Meilisearch) | Scoped tokens, never in client JS |

**Current:**
- `ADMIN_NAV_VISIBLE=false` default — Operator link hidden ✅
- Buyer must visit `/signin` before accounts/watchlist ✅
- Admin uses shared password, no CSRF token ⚠️
- `profile_id` is a bearer token — anyone with UUID can act as that profile ⚠️

---

## 4. Authorization & API safety

| Practice | Required |
|----------|----------|
| Profile scoping | All CRUD on accounts, watchlist, scheduled searches |
| No global side effects | Batch ingest/run must require `profile_id` or admin |
| Input validation | UUID format, bounds on limits |
| Rate limiting | Per-IP on `/api/*` and auth endpoints |

**Current:** `_validate_profile_id` on most routes ✅. `POST /api/scheduled-searches/run` without `profile_id` runs global batch ❌. No rate limiting ❌.

---

## 5. Session & cookie security

| Practice | Required |
|----------|----------|
| `SECRET_KEY` strong random | `DASHBOARD_SECRET_KEY` |
| `HttpOnly`, `Secure`, `SameSite` | On admin session cookie in prod |
| Session fixation | Regenerate session on login |

**Current:** Flask signed cookie for admin ⚠️ production flags not enforced.

---

## 6. Data protection

| Data | Risk | Mitigation |
|------|------|------------|
| Marketplace credentials in `connected_account.config` | High | Encrypt at rest (KMS or app-level); never return secrets in API JSON |
| Listing PII | Medium | Minimize storage; retention policy |
| API usage logs | Low | No tokens in query strings logged at INFO |

**Current:** Plaintext JSON config ❌. API masks labels but config may contain passwords ⚠️.

---

## 7. Dependency & supply chain

| Practice | Required |
|----------|----------|
| Pinned image tags | Docker compose |
| CI on every PR | pytest + ruff + gitleaks |
| Dependency updates | Periodic pip-audit or Dependabot |

**Current:** Pinned images ✅. CI ✅. No automated dep scan ⚠️.

---

## 8. Logging & monitoring

| Practice | Required |
|----------|----------|
| No secrets in logs | Redact tokens |
| Failed auth logging | Admin login failures |
| Anomaly detection | Optional — rate limit alerts |

**Current:** Gotify token in URL param convention — keep `LOG_LEVEL=WARNING` in prod documented ✅. No auth failure audit ⚠️.

---

## 9. Incident response

| Practice | Required |
|----------|----------|
| Contact / owner | In SECURITY.md |
| Revocation steps | Rotate secrets, invalidate sessions |
| Backup restore | PG restore tested |

**Current:** Partial documentation ⚠️.

---

## 10. Secure development

| Practice | Required |
|----------|----------|
| Threat model for new features | Profile in PR template or PLAN |
| Security tests | Authz tests for API routes |
| Pre-deploy checklist | SECURITY.md production table |

**Current:** `tests/test_web.py` admin auth tests ✅. Missing tests for profile isolation on accounts API ⚠️.

---

## Baseline audit (2026-06-24)

| Domain | Score | Top gap |
|--------|-------|---------|
| Secrets management | 6 | No startup validation |
| Network exposure | 7 | Incomplete prod compose |
| Authentication | 5 | UUID bearer; weak admin |
| Authorization | 4 | Global scheduled run |
| Session/cookies | 5 | No secure cookie flags |
| Data protection | 3 | Plaintext credentials |
| Supply chain | 7 | No dep scanner |
| Logging | 6 | Level not wired |
| Incident response | 4 | No runbook |
| Secure development | 5 | Missing authz tests |
| **Total** | **47** | |

---

## Hardening priority (P0 → P2)

1. **P0:** Require `profile_id` on scheduled batch; encrypt connected-account config; startup secret validation.
2. **P1:** Rate limits; deep health; Coolify full stack; secure admin cookies + CSRF.
3. **P2:** Signed buyer sessions; Dependabot; backup automation; IP allowlist for `/admin`.

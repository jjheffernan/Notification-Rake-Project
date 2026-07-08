# Security

Change all `change-me` values before non-local deploy. See `.env.example`.

## Auth models

| Surface | Path | Who |
|---------|------|-----|
| **Public buyer** | `/signin`, `/accounts`, `/watchlist` | Profile UUID created/restored client-side; required before private features |
| **Operator** | `/admin/login` → `/admin` | `ADMIN_USER` / `ADMIN_PASSWORD` — not linked from public nav when `ADMIN_NAV_VISIBLE=false` (default) |

For public hosting, keep `ADMIN_NAV_VISIBLE=false`. Operators reach `/admin/login` directly.

## Production checklist

| Secret | Notes |
|--------|-------|
| `POSTGRES_PASSWORD` | Strong random |
| `HASURA_ADMIN_SECRET` | Strong random; set `HASURA_ENABLE_CONSOLE=false` in Coolify |
| `GOTIFY_ADMIN_PASS` | Rotate after first login |
| `GOTIFY_TOKEN` | App token from Gotify UI |
| `DASHBOARD_SECRET_KEY` | Strong random; signs admin session |
| `ADMIN_PASSWORD` | Strong random; not `change-me` |
| `MEILISEARCH_API_KEY` | Required when Meilisearch is deployed |
| `CREDENTIAL_ENCRYPTION_KEY` | Fernet key for marketplace credentials; required in production |
| `JUPYTER_TOKEN` | Long random; keep Jupyter off public Traefik |

Set `ADMIN_NAV_VISIBLE=false` on any internet-facing deployment.

## Network

- Local compose binds `127.0.0.1` only.
- Coolify: Traefik for public `dashboard`, `hasura`, `gotify` — no public Postgres, Jupyter, Adminer, or Meilisearch.

## App

- `.env` gitignored.
- Gotify token in query param (API convention) — keep `LOG_LEVEL=WARNING` in prod.
- Marketplace credentials in `metadata.connected_account.config` are **encrypted at rest** (Fernet). Set `CREDENTIAL_ENCRYPTION_KEY` in production; API responses mask secrets (`storage/credential_crypto.py`).
- `profile_id` acts as a bearer token; treat UUID like a password — do not share links that embed it.
- `POST /api/scheduled-searches/run` requires `profile_id` — no global batch.
- Public `/api/*` and `/admin/login` are rate-limited (`web/rate_limit.py`).
- Admin login uses CSRF + `Secure`/`HttpOnly`/`SameSite` session cookies when `RAKE_ENV=production`.

## Reference

- [`docs/reference/security-practices.md`](docs/reference/security-practices.md)
- [`PLAN.md`](PLAN.md) — phased hardening tasks

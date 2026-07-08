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
| `JUPYTER_TOKEN` | Long random; keep Jupyter off public Traefik |

Set `ADMIN_NAV_VISIBLE=false` on any internet-facing deployment.

## Network

- Local compose binds `127.0.0.1` only.
- Coolify: Traefik for public dashboard (when added) — no public Postgres, Jupyter, or Adminer.

## App

- `.env` gitignored.
- Gotify token in query param (API convention) — keep `LOG_LEVEL=WARNING` in prod.
- Marketplace credentials are stored in `metadata.connected_account` (JSON). **Encrypt at rest before production** — see [`PLAN.md`](PLAN.md) Phase 2.
- `profile_id` acts as a bearer token; treat UUID like a password — do not share links that embed it.
- `POST /api/scheduled-searches/run` should require `profile_id` (planned — [`PLAN.md`](PLAN.md) Phase 0).

## Reference

- [`docs/reference/security-practices.md`](docs/reference/security-practices.md)
- [`PLAN.md`](PLAN.md) — phased hardening tasks

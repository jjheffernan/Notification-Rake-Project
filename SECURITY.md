# Security

Change all `change-me` values before non-local deploy. See `.env.example`.

## Production checklist

| Secret | Notes |
|--------|-------|
| `POSTGRES_PASSWORD` | Strong random |
| `HASURA_ADMIN_SECRET` | Strong random; set `HASURA_ENABLE_CONSOLE=false` in Coolify |
| `GOTIFY_ADMIN_PASS` | Rotate after first login |
| `GOTIFY_TOKEN` | App token from Gotify UI |
| `JUPYTER_TOKEN` | Long random; keep Jupyter off public Traefik |

## Network

- Local compose binds `127.0.0.1` only.
- Coolify: Traefik for Hasura/Gotify only — no public Postgres or Jupyter.

## App

- `.env` gitignored. Gotify token in query param (API convention) — keep `LOG_LEVEL=WARNING` in prod.
- MVP ingest = public RSS only; no stored marketplace credentials.

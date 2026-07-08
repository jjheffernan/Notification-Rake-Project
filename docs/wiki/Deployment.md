# Deployment

## Local / dev

See [Setup-and-Quick-Start](Setup-and-Quick-Start).

Always tear down when finished:

```bash
make down
```

## Production considerations

- Set `RAKE_ENV=production` and `ADMIN_NAV_VISIBLE=false` — see [Coolify environment matrix](#coolify-environment-matrix)
- Change all `change-me` secrets (startup validation rejects them in production)
- Do not expose Postgres, Adminer, Jupyter, Meilisearch, or Prometheus publicly
- Hasura: restrict admin secret; set `HASURA_ENABLE_CONSOLE=false`
- Dashboard: strong `DASHBOARD_SECRET_KEY` and `ADMIN_PASSWORD`
- Review [SECURITY.md](https://github.com/jjheffernan/Notification-Rake-Project/blob/main/SECURITY.md) in repo root

## Coolify on Proxmox

```text
Proxmox → LXC with Coolify → deploy/coolify/docker-compose.yml
```

1. Install [Coolify](https://coolify.io/docs) on LXC/VM.
2. Create Docker Compose resource pointing at `deploy/coolify/docker-compose.yml`.
3. Set environment variables in Coolify UI — see [Coolify environment matrix](#coolify-environment-matrix) below.
4. Traefik: public routes for buyer-facing services only; keep Postgres, app worker, Meilisearch, and dev tools on the internal network.
5. Optional: `COOLIFY_WEBHOOK` GitHub secret for auto-redeploy on `main`.

### Coolify environment matrix

Set these in the Coolify resource **Environment Variables** panel. Source of truth: [`.env.example`](https://github.com/jjheffernan/Notification-Rake-Project/blob/main/.env.example) and [`deploy/coolify/docker-compose.yml`](https://github.com/jjheffernan/Notification-Rake-Project/blob/main/deploy/coolify/docker-compose.yml).

#### Production defaults (required)

| Variable | Value | Why |
|----------|-------|-----|
| `RAKE_ENV` | `production` | App startup rejects placeholder secrets when set to `production` (see `config.py`). |
| `ADMIN_NAV_VISIBLE` | `false` | Hides the Operator link from public nav on internet-facing deploys. Operators use `/admin/login` directly. |

#### Secrets — must not stay `change-me`

Replace every placeholder before deploy. With `RAKE_ENV=production`, startup fails if any of these still match defaults:

| Variable | Default (invalid in prod) | Used by |
|----------|---------------------------|---------|
| `POSTGRES_PASSWORD` | `change-me` | `db`, Hasura, `app`, `dashboard` |
| `DATABASE_URL` | contains `change-me` | `app`, `dashboard` (auto-built from user/password if unset) |
| `HASURA_ADMIN_SECRET` | `change-me` | `hasura`, `app` |
| `GOTIFY_ADMIN_PASS` | `change-me` | `gotify` (first-login password) |
| `GOTIFY_TOKEN` | empty | `app` (required non-empty in production) |
| `DASHBOARD_SECRET_KEY` | `change-me-dashboard-secret` | `dashboard` (operator session signing) |
| `ADMIN_PASSWORD` | `change-me` | `dashboard` (operator login) |
| `MEILISEARCH_API_KEY` | `change-me-dev-key` | `meilisearch`, `app`, `dashboard` (required when Meilisearch is deployed or `SEARCH_ENGINE=meilisearch`) |
| `JUPYTER_TOKEN` | `change-me` | `jupyter` (dev-tools profile only) |

Generate strong random values for all secrets. See [SECURITY.md](https://github.com/jjheffernan/Notification-Rake-Project/blob/main/SECURITY.md).

#### Compose-enforced variables

These are referenced directly in `deploy/coolify/docker-compose.yml` (`${VAR:?set VAR}` = Coolify must set them):

| Variable | Default | Service | Notes |
|----------|---------|---------|-------|
| `POSTGRES_USER` | — | `db` | Required |
| `POSTGRES_PASSWORD` | — | `db` | Required; not `change-me` in prod |
| `POSTGRES_DB` | `rake` | `db` | Optional |
| `HASURA_ADMIN_SECRET` | — | `hasura` | Required |
| `HASURA_ENABLE_CONSOLE` | `false` | `hasura` | Keep `false` in production |
| `GOTIFY_ADMIN_PASS` | — | `gotify` | Required; Gotify admin password |
| `JUPYTER_TOKEN` | — | `jupyter` | Required when `dev-tools` profile is enabled |

#### App / dashboard / search

`deploy/coolify/docker-compose.yml` includes `dashboard`, `app`, and `meilisearch`. Set these in Coolify:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | auto-built | Postgres DSN for `app` and `dashboard` |
| `HASURA_URL` | `http://hasura:8080` | Internal GraphQL endpoint |
| `GOTIFY_URL` | `http://gotify:80` | Internal push API |
| `GOTIFY_PUBLIC_URL` | — | Public Gotify URL for admin dashboard links |
| `MEILISEARCH_URL` | `http://meilisearch:7700` | Internal search |
| `MEILISEARCH_API_KEY` | — | Meilisearch master key |
| `SEARCH_ENGINE` | `auto` | `auto` \| `postgres` \| `meilisearch` |
| `DASHBOARD_PORT` | `8000` | Container listen port |
| `ADMIN_USER` | `admin` | Operator username |
| `LOG_LEVEL` | `INFO` | Use `WARNING` in prod to reduce Gotify token noise in logs |
| `CREDENTIAL_ENCRYPTION_KEY` | — | Fernet key for marketplace credentials; required in production |

Ingestion, geocoding, FX, and marketplace toggles (`CRAIGSLIST_SEARCH_RSS`, `YAHOO_*`, `COPART_*`, `EU_*`, `CARSANDBIDS_*`, `NOMINATIM_URL`, `GEOCODE_USER_AGENT`, `FX_*`, `IMAGE_PROXY_ENABLED`, optional `FRED_API_KEY`, `CIS_AUTOMOTIVE_*`) follow `.env.example` — required only when those pipelines are enabled.

#### Service exposure (Traefik)

| Service | Exposure | Traefik | Notes |
|---------|----------|---------|-------|
| `dashboard` | **Public** | `traefik.enable=true` (Phase 1.2) | Buyer listings + `/signin`; operator at `/admin/login` |
| `hasura` | **Public** | `traefik.enable=true` | GraphQL API; lock down with `HASURA_ENABLE_CONSOLE=false` and strong admin secret |
| `gotify` | **Public** | `traefik.enable=true` | Push notification UI |
| `db` | Internal | — | Postgres — never expose publicly |
| `app` | Internal | — | Ingest/scripts worker — no Traefik labels |
| `meilisearch` | Internal | — | Search index — no Traefik labels |
| `jupyter` | Internal | — | `dev-tools` profile only; token auth, no public route |

> **Compose:** `deploy/coolify/docker-compose.yml` ships `db`, `hasura`, `gotify`, `meilisearch`, `dashboard`, and `app`. Optional `jupyter` via `dev-tools` profile.

## Hasura bootstrap

After first deploy, track tables in Hasura console or run:

```bash
make run CMD=hasura_track
```

## CI/CD

`.github/workflows/ci.yml`:

- Lint (ruff)
- pytest
- Gitleaks secrets scan
- pip-audit (supply-chain job)
- Docker build on PR/push
- Webhook deploy on `main` (if configured)

Post-deploy smoke: `scripts/ops/smoke_deploy.sh` (manual; E2E in CI is Phase 4).

## Scale path (future)

Redis/worker queue → OpenSearch → dedicated ingest workers. Not in MVP repo.

## Dashboard process

Production container command:

```text
gunicorn notification_rake.web:app --bind 0.0.0.0:8000 --workers 2
```

Defined in `docker/Dockerfile` dashboard target.

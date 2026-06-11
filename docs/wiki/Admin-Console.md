# Admin Console

Authenticated ops UI at `/admin`. Flask session cookie after login.

## Login

URL: `/admin/login`

Credentials: `ADMIN_USER` and `ADMIN_PASSWORD` from [Configuration](Configuration).

## Sections

### Stack health

Live probe of core and dev-tools services:

| Service | Internal check |
|---------|----------------|
| PostgreSQL | TCP + query |
| Hasura | HTTP health |
| Gotify | HTTP health |
| Prometheus | HTTP (dev-tools) |
| Metabase | HTTP (dev-tools) |
| JupyterLab | HTTP (dev-tools) |

Grey cards = service not running (start dev-tools profile) or unreachable.

Each card links to the public console URL when configured.

### Runtime actions

Whitelisted CLI commands executed in-process:

`health`, `pipeline`, `seed`, `hasura_track`, `ingest`, `normalize`, `upsert`

POST `/admin/actions/{name}` (form) or `/admin/api/actions/{name}` (JSON, session required).

### Database layers

Counts: search listings, raw listings, catalog models, job runs, sources.

### Sources

Enable/disable rows in `listings.source` — toggles future ingest per source.

### Catalog

Add make/model pairs to reference catalog (`add_vehicle_model`).

### Job history

Recent rows from `metadata.job_runs`.

## JSON API

`GET /admin/api/overview` — full dashboard payload for auto-refresh (requires admin session).

## Code

| Module | Role |
|--------|------|
| `admin/console.py` | Health, stats, `execute_action()` |
| `web/blueprints/admin.py` | Routes |
| `web/auth.py` | Session verification |
| `web/static/admin.js` | Client refresh (if present) |

See [Architecture](Architecture) for package layout.

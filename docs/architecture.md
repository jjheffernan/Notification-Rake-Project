# Architecture

Product vision: [`specs.md`](../specs.md). Wiki: [Architecture](wiki/Architecture.md).

## Data layers (single Postgres instance)

| Schema | Purpose | Key tables |
|--------|---------|------------|
| `public` | Search (PostGIS) | `vehicle_listing`, `vehicle_make`, `vehicle_model` |
| `reference` | Canonical catalog | views + `vehicle_trim`, `vehicle_generation`, `vehicle_body_style` |
| `listings` | Raw marketplace records | `source`, `seller`, `listing`, `listing_image`, `listing_history` |
| `metadata` | Operations | `job_runs`, `crawler_status`, `sync_status`, `api_usage`, `saved_search` |

## Pipeline flow

```text
Craigslist RSS (live)
  → ingest → raw store → normalize → geocode
  → upsert vehicle_listing → Gotify alerts → job_runs

Yahoo Auctions JP (phase 0 client, pipeline TBD)
  → search API auccat=26360 → future ingest
```

## Python packages

```text
models/         VehicleListing
ingestion/      craigslist, raw, yahoo/
transform/      normalize, geocode
storage/        db, metadata, migrations
search/         ListingSearch, REST-backed queries
workflow/       pipeline
integrations/   hasura, gotify
notifications/  alerts
admin/          console (health, actions)
web/            Flask — blueprints: public, admin
```

## Web application

| Component | Technology |
|-----------|------------|
| HTTP server | gunicorn → `notification_rake.web:app` |
| Public routes | `web/blueprints/public.py` |
| Admin routes | `web/blueprints/admin.py` |
| Map | Leaflet + OSM tiles |
| Session auth | Flask + `DASHBOARD_SECRET_KEY` |

Public dashboard: split map/list search, facets, price history modal. See [wiki/Dashboard-and-Search.md](wiki/Dashboard-and-Search.md).

## Compose services

| Service | Role | Auth |
|---------|------|------|
| `db` | PostGIS + layered schemas | Postgres credentials |
| `hasura` | GraphQL API | Admin secret |
| `gotify` | Push notifications | Admin password |
| `dashboard` | Public search + admin console | Public / admin session |
| `app` | CLI (`python -m notification_rake`) | — |
| `jupyter` (dev-tools) | Notebooks | Token |
| `adminer` (dev-tools) | DB browser | Server login |
| `metabase` (dev-tools) | Analytics | Admin setup |
| `grafana` + `prometheus` (dev-tools) | Monitoring | Grafana admin |

## URLs (local)

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000 | Public dashboard (map + search) |
| http://127.0.0.1:8000/admin | Admin console |
| http://127.0.0.1:8080/console | Hasura |
| http://127.0.0.1:8081 | Gotify |
| http://127.0.0.1:8082 | Adminer |
| http://127.0.0.1:3000 | Metabase |
| http://127.0.0.1:3001 | Grafana |
| http://127.0.0.1:8888 | JupyterLab |

Deploy: [`deploy.md`](deploy.md). Modules: [`functions.md`](functions.md).

# Architecture

## Data layers (single Postgres / PostGIS)

| Schema | Purpose | Key objects |
|--------|---------|-------------|
| `public` | Search index | `vehicle_listing`, `vehicle_make`, `vehicle_model`, PostGIS `geom` |
| `reference` | Catalog | trims, generations, body styles |
| `listings` | Raw marketplace | `source`, `seller`, `listing`, `listing_image`, `listing_history` |
| `metadata` | Operations | `job_runs`, `crawler_status`, `sync_status`, `api_usage`, `saved_search` |

## Pipeline flow

```text
Source fetch (Craigslist RSS)
  → VehicleListing (models/)
  → store_raw_listings (listings schema)
  → normalize + geocode (transform/)
  → upsert vehicle_listing (storage/)
  → notify_new_listings (Gotify)
  → finish_job (metadata/)
```

Yahoo Auctions JP (phase 0 client ready, pipeline wiring phase 1): see [Yahoo-Auctions-JP](Yahoo-Auctions-JP).

## Python package layout

```text
src/notification_rake/
  config.py
  models/           VehicleListing
  ingestion/        craigslist, raw, yahoo/
  transform/        normalize, geocode
  storage/          db, metadata, migrations
  search/           buyer search service
  workflow/         pipeline orchestration
  integrations/     hasura, gotify
  notifications/    alerts
  admin/            runtime console
  web/              Flask app
    blueprints/     public, admin
    static/         dashboard.js, dashboard.css
    templates/
```

## Docker Compose

**Core profile** (`make up`):

| Service | Image / build | Port |
|---------|---------------|------|
| `db` | postgis/postgis:16 | 5432 |
| `hasura` | graphql-engine | 8080 |
| `gotify` | gotify/server | 8081 |
| `dashboard` | Flask `gunicorn notification_rake.web:app` | 8000 |
| `app` | CLI entrypoint | — |

**dev-tools profile**:

| Service | Port |
|---------|------|
| jupyter | 8888 |
| adminer | 8082 |
| metabase | 3000 |
| grafana | 3001 |
| prometheus | 9090 |

Admin console health checks use internal Docker hostnames (`db`, `hasura`, `jupyter`, etc.). Dev-tools services show **skip/fail** until the dev-tools profile is started.

## Auth model

| Surface | Auth |
|---------|------|
| Public dashboard `/` | None |
| Public REST `/api/*` | None |
| Admin `/admin/*` | Session cookie (`DASHBOARD_SECRET_KEY`) |
| Hasura | `HASURA_ADMIN_SECRET` |
| Jupyter | `JUPYTER_TOKEN` |

See [Dashboard-and-Search](Dashboard-and-Search) and [Admin-Console](Admin-Console).

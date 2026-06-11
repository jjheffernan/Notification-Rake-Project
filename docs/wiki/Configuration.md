# Configuration

All settings load from environment variables via `src/notification_rake/config.py`. Copy `.env.example` to `.env`.

## Database

| Variable | Default | Purpose |
|----------|---------|---------|
| `POSTGRES_USER` | `rake` | Postgres user |
| `POSTGRES_PASSWORD` | `change-me` | Postgres password |
| `POSTGRES_DB` | `rake` | Database name |
| `DATABASE_URL` | auto-built | Full DSN for app/dashboard |

## Ingestion — Craigslist

| Variable | Purpose |
|----------|---------|
| `CRAIGSLIST_SEARCH_RSS` | RSS search URL for pipeline |

## Ingestion — Yahoo Auctions JP (phase 0)

| Variable | Default | Purpose |
|----------|---------|---------|
| `YAHOO_APP_ID` | empty | Yahoo Developer Application ID |
| `YAHOO_AUCTION_API_BASE` | `https://auctions.yahooapis.jp/AuctionWebService/V2` | API base |
| `YAHOO_VEHICLE_AUCCAT` | `26360` | Used/new car category |
| `YAHOO_INGEST_PAGE_SIZE` | `50` | Results per page (max 50) |
| `YAHOO_REQUESTS_PER_DAY` | `45000` | Client soft rate cap |
| `DEFAULT_DEST_COUNTRY` | `US` | Future proxy quotes |
| `FX_USD_JPY` | `150.0` | FX display (future) |

Without `YAHOO_APP_ID`, the Yahoo client uses a bundled JSON fixture.

See [Yahoo-Auctions-JP](Yahoo-Auctions-JP).

## Geocoding

| Variable | Purpose |
|----------|---------|
| `NOMINATIM_URL` | Nominatim base URL |
| `GEOCODE_USER_AGENT` | Required User-Agent for Nominatim |

## Dashboard / admin

| Variable | Purpose |
|----------|---------|
| `DASHBOARD_PORT` | Host port (default 8000) |
| `DASHBOARD_SECRET_KEY` | Flask session signing |
| `ADMIN_USER` | Admin login username |
| `ADMIN_PASSWORD` | Admin login password |

## Integrations

| Variable | Purpose |
|----------|---------|
| `HASURA_URL` / `HASURA_ADMIN_SECRET` | GraphQL engine |
| `GOTIFY_URL` / `GOTIFY_TOKEN` | Push notifications |
| `GOTIFY_PUBLIC_URL` | Browser link in admin |

## Dev tool URLs (admin dashboard links)

| Variable | Default |
|----------|---------|
| `ADMINER_URL` | http://127.0.0.1:8082 |
| `METABASE_URL` | http://127.0.0.1:3000 |
| `GRAFANA_URL` | http://127.0.0.1:3001 |
| `JUPYTER_URL` | http://127.0.0.1:8888 |
| `METABASE_INTERNAL_URL` | http://metabase:3000 |
| `PROMETHEUS_INTERNAL_URL` | http://prometheus:9090 |
| `JUPYTER_INTERNAL_URL` | http://jupyter:8888 |

Internal URLs are used by the admin health checker inside Docker.

## Jupyter

| Variable | Purpose |
|----------|---------|
| `JUPYTER_TOKEN` | Lab login token |
| `JUPYTER_PORT` | Host port |

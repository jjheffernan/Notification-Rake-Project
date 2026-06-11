# Custom logic reference

Product: [`specs.md`](../specs.md). Architecture: [`architecture.md`](architecture.md). Wiki: [API-Reference](wiki/API-Reference.md).

## Package layout

```text
notification_rake/
  config.py
  models/             VehicleListing
  ingestion/          craigslist, raw, yahoo/
  transform/          normalize, geocode
  storage/            db, metadata, migrations
  search/             buyer search service
  workflow/           pipeline
  integrations/       hasura, gotify
  notifications/      alerts
  admin/              console
  web/                Flask (public + admin blueprints)
```

## `config.py`

Env-backed settings: Postgres, Gotify, Hasura, geocoding, dashboard admin, Yahoo Auctions (`YAHOO_*`), tool URLs. See [wiki/Configuration.md](wiki/Configuration.md).

## `models/listing.py`

`VehicleListing` — normalized in-memory shape for ingest/normalize.

## `ingestion/craigslist.py`

RSS fetch/parse. `fetch_listings()` — 403 → sample fixture in dev.

## `ingestion/yahoo/`

Phase 0 Yahoo Auctions JP — [yahoo-setup.md](yahoo-setup.md).

| Symbol | Role |
|--------|------|
| `YahooClient` | appid, daily budget, JSON/JSONP |
| `search_vehicle_auctions()` | `auccat=26360` search |
| `YahooAuctionHit` | Normalized hit + proxy deep links |
| `load_sample_search()` | Offline fixture |

## `ingestion/raw.py`

`store_raw_listings()` → `listings` schema + history.

## `transform/normalize.py`

Title → canonical make/model via Postgres catalog.

## `transform/geocode.py`

Nominatim + Craigslist region centroids.

## `storage/db.py`

`seed_catalog`, `upsert_listings`, `search_within_radius`, `add_vehicle_model`, `list_listings`.

## `storage/metadata.py`

`start_job`, `finish_job`, `list_job_runs`, `record_api_usage`.

## `workflow/pipeline.py`

`run_pipeline()` — full ingest → alert orchestration.

## `search/service.py`

| Symbol | Role |
|--------|------|
| `ListingSearch` | Filter dataclass |
| `search_listings()` | Paginated + price_delta |
| `get_listing_detail()` | Price history |
| `search_facets()` | Source/make counts |
| `market_summary()` | Per-source stats |

## `web/` (Flask + gunicorn)

### Blueprints

| File | Routes |
|------|--------|
| `blueprints/public.py` | `/`, `/api/*`, `/health` |
| `blueprints/admin.py` | `/admin/*` |

### Static UI

| File | Role |
|------|------|
| `static/dashboard.js` | Search, infinite scroll, Leaflet map, split/list/map toggle |
| `static/dashboard.css` | Layout, map panel, cards |
| `templates/dashboard.html` | Search form + map + feed |

### Routes

| Route | Auth | Purpose |
|-------|------|---------|
| `/` | Public | Dashboard |
| `/api/listings` | Public | JSON search |
| `/api/listings/{id}` | Public | Detail + history |
| `/api/facets` | Public | Dynamic filters |
| `/api/market/summary` | Public | Market bar |
| `/admin/login` | — | Sign in |
| `/admin` | Session | Ops console |
| `/admin/api/overview` | Session | JSON status |
| `/admin/api/actions/{name}` | Session | Run script |

## `admin/console.py`

`check_services`, `layer_stats`, `execute_action`, `admin_overview`, source toggle, catalog add.

## Container scripts

`health`, `ingest`, `normalize`, `upsert`, `pipeline`, `seed`, `hasura_track`, `add_model`

```bash
python -m notification_rake pipeline
make run CMD=pipeline
```

Dashboard process: `gunicorn notification_rake.web:app`

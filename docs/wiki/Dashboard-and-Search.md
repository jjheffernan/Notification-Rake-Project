# Dashboard and Search

Public buyer UI at `/`. No authentication. Flask + Jinja2 + Leaflet.

## Layout

1. **Search panel** — filters, sort, save search
2. **Map + results** — split view (default), list-only, or map-only
3. **Listing detail** — modal with price history

## Search filters

| Field | API param | Notes |
|-------|-----------|-------|
| Keywords | `q` | Title/text search |
| Make / model | `make`, `model` | Catalog names |
| Source | `source` | Tab or dropdown |
| Region | `country` | ISO code (`US`, `JP`, …) |
| Year range | `year_min`, `year_max` | |
| Price range | `price_min`, `price_max` | USD for US listings |
| Radius | `radius_km` → `radius_m` | From **search center** (blue dot), not live map pan |
| Sort | `sort` | `updated_desc`, `price_asc`, `price_desc`, `year_desc`, `distance` |

## Search backend

- **Postgres/PostGIS** — source of truth for listings and geo radius
- **Meilisearch** (`SEARCH_ENGINE=auto`) — full-text + filtered search when healthy; falls back to Postgres
- Pipeline and admin **search_reindex** sync listings into Meilisearch after ingest

## Map view

- **Split** (default on desktop): sticky map left, scrollable cards right
- **List** / **Map**: full-width single pane
- **Search center** — fixed when you run Search; blue dot + radius circle show the geo filter
- **Pan freely** — viewport is independent; explore loaded pins without re-querying
- **Search this area** — optional; moves search center to map center and re-runs the query
- **Lazy load** — infinite scroll loads pages of 24; client cache (5 min) prefers cached pages before network
- Pins sync with cards (hover/click highlights)
- Stats line: `N in search · M loaded · K pinned · V in view`

Map library: [Leaflet](https://leafletjs.com/) + OpenStreetMap tiles.

Default map center comes from `default_lat` / `default_lon` in config (SF Bay unless changed).

## Source tabs

AutoTempest-style tabs built from `/api/facets` — click to filter by source.

## Saved searches

Stored in browser `localStorage` (client-side only). Server-side alerts via `metadata.saved_search` planned.

## Price drops

Cards show a badge when `price_delta` is negative (derived from `listing_history` on ingest refresh).

## Market summary bar

`/api/market/summary` — per-source listing count and average price.

## Static assets

| File | Role |
|------|------|
| `web/templates/dashboard.html` | Page shell |
| `web/static/dashboard.js` | Search, map, infinite scroll |
| `web/static/dashboard.css` | Dark theme layout |

## Related

- [API-Reference](API-Reference) — JSON endpoints
- [Ingestion-Pipeline](Ingestion-Pipeline) — how data gets into search layer

# Notification Rake — product spec

Self-hosted car market aggregator. Buyer-first. No dealer lead game.

Inspired by [Visor](https://visor.vin/) (whole market, map, price history, buyer focus) and [AutoTempest](https://www.autotempest.com/) (multi-source one search, filters, saved searches, sort).

## Core job

Collect listings (where permitted) → normalize make/model → geo index → search + alert. One query across sources.

## Buyer UX (public, no login)

- Unified search: make/model/text/VIN fragment across all ingested sources
- Filter: source, **region (US/CA/JP/GB/DE)**, year, price, mileage, radius from map point (not zip-only)
- **Import eligibility toggles**: US 25-year rule, Canada 15-year rule (badges on cards)
- Sort: price, year, distance, newest, price drop
- View: split map + scroll feed (Split / List / Map toggle); pins sync with cards; radius circle; search-this-area on pan
- Listing detail: full price history from `listing_history`
- Saved searches in browser; optional alert hook (Gotify) when new match
- Source tabs: all sources or one (AutoTempest-style)

## Market layer (Visor-like, phase 2)

- Facets: counts by make/model/source update as filters change
- Summary stats: avg price, listing count, price change vs first seen
- Regional days-on-market when scrape cadence allows

## Data layers (Postgres schemas)

reference — vehicle_make, vehicle_model, vehicle_trim, vehicle_generation, vehicle_body_style  
listings — source, seller, listing, listing_image, listing_history (raw + audit)  
public — vehicle_listing + PostGIS geom (search index, rebuilt from listings)  
metadata — job_runs, crawler_status, sync_status, saved_search, api_usage

## Ingestion sources (expand over time)

MVP: Craigslist RSS (sample fallback in dev)  
Phase 0: Yahoo Auctions JP (`auccat=26360`) — client + notebook; pipeline phase 1  
Copart (US/UK/DE), eBay (US/UK/DE), Gumtree, AutoScout24, mobile.de, **Cars & Bids** — see [`docs/wiki/EU-Marketplaces.md`](docs/wiki/EU-Marketplaces.md), [`docs/wiki/Cars-and-Bids.md`](docs/wiki/Cars-and-Bids.md)  
**Market data pages** — `/m/<make>/<model>` classic.com-style views — [`docs/wiki/Market-Data.md`](docs/wiki/Market-Data.md)  
Target: Autotrader, CarGurus, Facebook Marketplace — `listings.source` enable/disable in admin  
Proxy overlay (Buyee, Neokyo, FromJapan): landed-cost compare on Yahoo listings — phase 3

## Web stack

Flask + gunicorn. Public blueprints + admin blueprints. Leaflet map in search (split/list/map modes).

## API surface

- Hasura GraphQL on tracked tables (admin secret)
- Public REST: `/api/listings`, `/api/listings/{id}`, `/api/facets`, `/api/market/summary`
- Admin console: stack health, run pipeline, source toggle, catalog add

## Ops stack (docker compose)

db (PostGIS), hasura, gotify, dashboard, app CLI  
dev-tools: jupyter, adminer, metabase, grafana, prometheus

Admin auth only. Public browse open.

Docs: [`docs/wiki/Home.md`](docs/wiki/Home.md) (GitHub Wiki–ready).

## Non-goals (MVP)

- Dealer CRM / lead resale
- "Good deal" badge without transparent data
- Custom JupyterHub (single Jupyter dev profile OK for now)

## Success

User open dashboard → filter Toyota Camry within 50mi → see map + list → spot price drop from history → save search → get Gotify ping on new match.

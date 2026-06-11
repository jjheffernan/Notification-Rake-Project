# Cars & Bids Ingestion

[Cars & Bids](https://carsandbids.com) is a US enthusiast auction platform (1980s+ modern classics) with detailed condition reports and public sold results.

## Source

| Field | Value |
|-------|-------|
| Slug | `carsandbids` |
| Country | US |
| Type | Enthusiast auction |

## Status

| Phase | State |
|-------|-------|
| Fixture ingest | Done |
| Connector (connected accounts) | Done |
| Pipeline (`ingest_all`) | Done |
| Live API / scrape | Planned |

## Module layout

```
src/notification_rake/ingestion/carsandbids/
  client.py    — HTTP client, fixture fallback
  search.py    — CarsAndBidsLot, search_auctions()
  normalize.py — lot → VehicleListing
fixtures/carsandbids_sample.json
```

## Config

```env
CARSANDBIDS_ENABLED=true
CARSANDBIDS_API_MODE=auto      # auto | fixture | provider
CARSANDBIDS_API_KEY=           # third-party parser key when wired
CARSANDBIDS_INGEST_LIMIT=50
```

## Ingest

```bash
docker compose run --rm app carsandbids
docker compose run --rm app ingest_all   # includes Cars & Bids when enabled
```

Admin action: `ingest_carsandbids`

## Connected account

```json
{"query": "Stagea", "mode": "active", "limit": 20}
```

Modes: `active` (live), `past` (sold), or omit for all fixtures.

## Metadata

Listings carry auction fields in `metadata`:

- `auction_status`, `ends_at`, `current_bid`, `sold_price`
- `bid_count`, `reserve_met`, `location`, `listing_url`
- Badges: `Cars & Bids`, `Live auction`, `Sold`, `Reserve met`

## Live integration (planned)

Cars & Bids has no public API. Options for production:

1. Third-party parser (Carapis, Apify actor) via `CARSANDBIDS_API_KEY`
2. Self-hosted scrape of `/search/<make>` with JS rendering + rate limits
3. Manual URL watchlist via connected account `detail` mode

Sold-price history from past auctions feeds the market data page price trend.

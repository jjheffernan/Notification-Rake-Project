# API Reference

## Public REST (Flask)

No authentication. Base URL: `http://127.0.0.1:8000`

### `GET /api/listings`

Paginated search.

| Param | Type | Notes |
|-------|------|-------|
| `q` | string | Keywords |
| `make`, `model` | string | |
| `source` | string | |
| `year_min`, `year_max` | int | |
| `price_min`, `price_max` | float | |
| `lat`, `lon` | float | Map center |
| `radius_m` | float | 1000–500000 |
| `sort` | string | See [Dashboard-and-Search](Dashboard-and-Search) |
| `limit` | int | 1–100, default 24 |
| `offset` | int | Pagination |

Response:

```json
{
  "items": [{ "id", "title", "price", "year", "make", "model", "lat", "lon", "meters", "price_delta", "price_events", ... }],
  "total": 42,
  "limit": 24,
  "offset": 0
}
```

### `GET /api/listings/{id}`

Detail + `price_history` array.

### `GET /api/facets`

Dynamic counts for `sources` and `makes` given current filters (no pagination params).

### `GET /api/market/summary`

Per-source `listings`, `avg_price`, `min_price`, `max_price`.

### `GET /health`

```json
{ "status": "ok" }
```

## Admin REST

Requires admin session cookie (login via `/admin/login`).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/api/overview` | Stack + layer stats JSON |
| POST | `/admin/api/actions/{name}` | Run pipeline action |

## GraphQL (Hasura)

URL: `http://127.0.0.1:8080/v1/graphql`

Header: `x-hasura-admin-secret: {HASURA_ADMIN_SECRET}`

Tracked tables include `vehicle_listing`, `vehicle_make`, `vehicle_model`, listings schema, metadata.

Bootstrap:

```bash
make run CMD=hasura_track
```

## Search module (Python)

Import from `notification_rake.search`:

- `ListingSearch` — filter dataclass
- `search_listings(dsn, search)`
- `get_listing_detail(dsn, id)`
- `search_facets(dsn, search)`
- `market_summary(dsn)`

Implementation: `search/service.py`.

## Yahoo client (Python, phase 0)

Import from `notification_rake.ingestion.yahoo`:

- `search_vehicle_auctions(**kwargs)`
- `YahooClient.from_settings()`

Not yet exposed via HTTP — ingest only.

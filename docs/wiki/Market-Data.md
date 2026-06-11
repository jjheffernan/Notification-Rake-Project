# Market Data Pages

Classic.com-style make/model market views for managing and exploring search data.

## Pages

| URL | Description |
|-----|-------------|
| `/m` | Market index — browse all indexed make/model pairs |
| `/m/<make>/<model>` | Model snapshot — stats, charts, comps (e.g. `/m/nissan/stagea`) |

## API

| Endpoint | Returns |
|----------|---------|
| `GET /api/market/models` | Index of make/model pairs with listing counts and price stats |
| `GET /api/market/model?make=&model=` | Full market snapshot for one model |
| `GET /api/market/<make_slug>/<model_slug>` | Same as above, slug-based |

### Model snapshot includes

- **Summary** — median, average, min/max, year range, avg mileage
- **By year** — listing count and avg price per model year
- **By source** — breakdown across Craigslist, Copart, Cars & Bids, etc.
- **By region** — country breakdown
- **Price trend** — monthly average from `listing_history`
- **Comps** — recent comparable listings with price deltas
- **Sales volume** — inventory by year, new listings per month, market activity
- **External data** (optional) — Wikipedia production, EPA model years, NHTSA catalog, FRED US sales trend, CIS dealer sales

## External data sources

Configure optional keys in `.env` to enrich model pages:

| Variable | Source | Data |
|----------|--------|------|
| `FRED_API_KEY` | [FRED](https://fred.stlouisfed.org/) | US total vehicle sales (TOTALSA SAAR) |
| `CIS_AUTOMOTIVE_JWT` or `CIS_AUTOMOTIVE_API_KEY` + `SECRET` | [CIS Automotive](https://autodealerdata.com/) | US dealer brand sales, regional model rank |
| *(none)* | Wikipedia, EPA, NHTSA | Production figures, US model years, catalog match |

Wikipedia, EPA FuelEconomy.gov, and NHTSA vPIC are called without keys (best-effort).

## Workflow

1. Ingest listings from multiple sources (`ingest_all`)
2. Normalize make/model via catalog matching
3. Browse `/m` or jump from Search via **Market data** nav
4. Open a model page to review pricing before setting saved searches

## Link from search

When filtering by make + model on the dashboard, use **Market data** → find the model, or go directly to `/m/<make-slug>/<model-slug>`.

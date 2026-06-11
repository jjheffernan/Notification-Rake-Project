# Ingest Routes

Each market/source group has an **isolated ingest pipeline** — separate fetch, sync, job tracking, and search filter.

## Routes

| Slug | Label | Sources | CLI / Admin |
|------|-------|---------|-------------|
| `us-retail` | US retail | craigslist, ebay | `ingest_us_retail`, `pipeline` |
| `us-auction` | US auctions | copart, carsandbids | `ingest_us_auction` |
| `jp` | Japan | yahoo_auctions_jp | `ingest_jp` |
| `uk` | United Kingdom | ebay_uk, gumtree, autoscout24_uk, copart_uk | `ingest_uk` |
| `de` | Germany | mobile_de, autoscout24_de, ebay_de, copart_de | `ingest_de` |
| `connected` | Connected accounts | (profile-linked) | `/accounts` → Sync |

Single-source routes (`copart`, `carsandbids`, `craigslist`, etc.) also exist for granular ingest.

## Running pipelines

```bash
# One route
docker compose run --rm app ingest_jp
docker compose run --rm app ingest_us_auction

# All bulk routes (isolated — one failure does not block others)
docker compose run --rm app ingest_all
```

Admin actions: `ingest_us_retail`, `ingest_us_auction`, `ingest_jp`, `ingest_uk`, `ingest_de`, `ingest_all`.

Each route logs a separate job as `route:<slug>` in `metadata.job_run`.

## Search by route

Dashboard **Route** filter (or API `?route=jp`) scopes results to that pipeline's sources.

```
GET /api/routes          — route catalog + listing counts
GET /api/listings?route=us-auction
```

Route takes precedence over **Source** when both are set. Selecting a route auto-fills the matching **Region** when applicable.

## Code

- Registry: `models/ingest_routes.py`
- Pipeline runner: `workflow/routes.py`
- Legacy wrapper: `workflow/multi_source.py`

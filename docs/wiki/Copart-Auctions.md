# Copart auctions (US)

Roadmap: [`plans/copart-auction-ingestion.md`](../plans/copart-auction-ingestion.md). Official site: [copart.com](https://www.copart.com).

Copart is a **salvage and insurance auction** source — distinct from Craigslist retail listings. Inventory is keyed by **lot number**, includes **damage/title/run-drive** metadata, and ships with **large photo galleries** tied to **yard locations**.

## Status

| Phase | Scope | Status |
|-------|--------|--------|
| 0 | Discovery spike, fixtures, endpoint catalog | Done |
| 1 | Search + detail ingest, dashboard Copart tab | Done |
| 1b | Hotlink/proxy images (no blob storage) | Done |
| 2 | Damage/title analysis, auction facets | Done |
| 3 | Multi-source pipeline + connected account sync | Done |
| 4 | Live auction poll, Gotify alerts | Planned |

## Why Copart

- ~250k+ live US lots; strong fit for **US region** filter (`country=US`)
- Yard geo coordinates map to existing PostGIS + map UI
- Auction price history maps to `listing_history`
- Complements Craigslist (retail) and Yahoo JP (export auctions)

## Access strategy

Copart has **no public developer API**. Planned tiers:

1. **Licensed aggregator API** (e.g. [Apibara](https://apibara.tech/en/products/vehicle-auction-data-api/docs), [Carapis](https://www.carapis.com/platforms/global/copart)) — preferred for production
2. **Web/XHR capture** — self-hosted fallback with fixtures for dev
3. **Fixtures** — offline samples like Craigslist RSS fallback

## Workflows (summary)

| Workflow | Purpose |
|----------|---------|
| Discovery sweep | Find lots by make/model/state/status |
| Detail refresh | Full specs, gallery URLs, bid updates |
| Media hydration | Download/cache images, thumbnails, dedupe |
| Metadata analysis | VIN decode, damage/title normalization |
| Public sync | Normalize → `vehicle_listing` → Meilisearch |

## Data highlights

| Field | Buyer use |
|-------|-----------|
| `lot_number` | Primary key; link to Copart |
| Damage primary/secondary | Rebuild cost signal |
| Title type | Salvage vs clean |
| Run & drive / keys | Mobility |
| Yard location | Map + shipping |
| Gallery | Full media hydration pipeline |

## Config (planned)

See [copart-auction-ingestion.md](../plans/copart-auction-ingestion.md#config-additions) for `COPART_*` and `COPART_MEDIA_*` variables.

## Related

- [Yahoo-Auctions-JP](Yahoo-Auctions-JP) — JP auction template
- [Ingestion-Pipeline](Ingestion-Pipeline) — shared raw → public flow
- [Dashboard-and-Search](Dashboard-and-Search) — region + source filters

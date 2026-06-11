# Ingestion Pipeline

## Overview

```text
ingest → store_raw_listings → normalize → geocode → upsert → alert → job metadata
```

Entry point: `workflow/pipeline.py` → `run_pipeline()`.

## Active source: Craigslist RSS

| Module | Function |
|--------|----------|
| `ingestion/craigslist.py` | `fetch_listings()` — RSS GET + parse |
| `ingestion/raw.py` | `store_raw_listings()` — `listings` schema |
| `transform/normalize.py` | Title → make/model via catalog |
| `transform/geocode.py` | Coordinates (Nominatim + region fallback) |
| `storage/db.py` | `upsert_listings()` → `vehicle_listing` |
| `notifications/alerts.py` | Gotify on new inserts |

**Dev fallback:** Craigslist often returns 403 from datacenter IPs — pipeline uses bundled RSS fixture automatically.

Configure search URL: `CRAIGSLIST_SEARCH_RSS` in `.env`.

## CLI commands

```bash
make run CMD=pipeline    # full run
make run CMD=ingest      # fetch only
make run CMD=normalize   # catalog match
make run CMD=upsert      # ingest + normalize + sync
make run CMD=seed        # seed make/model catalog
make run CMD=hasura_track
```

## Catalog

Default makes/models seeded on pipeline run (`seed_catalog`). Add via admin catalog form or:

```bash
make run CMD=add_model   # via scripts/add_model.py
```

## Raw vs search layer

| Layer | Table(s) | Purpose |
|-------|----------|---------|
| Raw | `listings.listing`, `listing_history` | Audit trail, price history |
| Search | `public.vehicle_listing` | Geo-indexed buyer search |

Price history in the dashboard comes from joining search listings to raw history.

## Planned sources

| Source | Status |
|--------|--------|
| Craigslist RSS | **Live** |
| Yahoo Auctions JP (`auccat=26360`) | Phase 0 client; pipeline phase 1 |
| Autotrader, CarGurus, Facebook | Spec only |

Enable/disable via `listings.source.enabled` and admin source toggle.

## Hasura

After schema changes:

```bash
make run CMD=hasura_track
```

Tracks `public`, `listings`, and `metadata` tables for GraphQL.

See [Yahoo-Auctions-JP](Yahoo-Auctions-JP) for Japan auction ingest plan.

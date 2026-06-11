# Logic audit

## Current state (2026-06)

| Area | Status |
|------|--------|
| Layered Postgres schemas | Implemented (`db/init/`) |
| Craigslist ingest + pipeline | Live with RSS + fixture fallback |
| PostGIS search + radius | Live |
| Flask public dashboard | Live — split map/list, facets, history modal |
| Flask admin console | Live — health, actions, sources |
| Yahoo Auctions client | Phase 0 — client + tests, not in pipeline yet |
| Gotify alerts | Live on new upserts |
| Hasura track script | Live |
| Saved search server alerts | Schema only; client uses localStorage |
| Proxy quote layer (Buyee/Neokyo) | Planned |

Package layout reorganized from flat modules → `models/`, `ingestion/`, `transform/`, `storage/`, `search/`, `workflow/`, `web/`, etc.

Web stack migrated FastAPI → Flask (gunicorn).

## Historical notes (2025-06)

Early MVP audit — some items below are **resolved**; kept for context.

| Item | Original verdict | Now |
|------|------------------|-----|
| No DB write from Python | Gap | **Done** — `upsert_listings` |
| Flat `ingestion/` packages | Removed as premature | **Restored** as proper package tree |
| Celery/worker stub | Removed | Still deferred |
| `rust/rake-matcher/` | Removed placeholder | Still absent |

See [functions.md](functions.md) and [wiki/Home.md](wiki/Home.md) for current module map.

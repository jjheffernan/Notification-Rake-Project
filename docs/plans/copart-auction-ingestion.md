# Copart auction ingestion plan

Goal: ingest **[Copart](https://www.copart.com)** salvage and used-vehicle auction lots into Notification Rake with **full media hydration**, **structured metadata analysis**, and **buyer-focused search** — same unified dashboard as Craigslist (US retail) and Yahoo JP (auctions).

Copart is not a dealer listing site. It is an **insurance/salvage auction marketplace** (~250k+ live lots, millions sold per year). Listings are keyed by **lot number**, carry **damage/title/run-drive** semantics, and ship with **large photo galleries** tied to physical **yard locations**. That makes Copart a distinct source type: auction + condition metadata + geo at the yard, not the seller’s driveway.

---

## Strategy

**One canonical listing per Copart lot number.** Do not duplicate Copart inventory on IAAI or third-party resellers unless we later add IAAI as a separate source with explicit crosswalk.

```text
Copart (source of truth: lot #)
  → discovery search / lot detail ingest
  → raw preserve + media URL catalog
  → async media hydration (mirror or proxy)
  → metadata analysis (VIN, damage, title, specs)
  → normalize → VehicleListing + auction extensions
  → public search (US region) + Meilisearch index

Buyer UX
  → map pins at yard location
  → gallery + damage/title badges
  → auction countdown + bid history
  → link out to Copart for purchase (no bid automation v1)
```

Why Copart fits this product:

- Buyer-first aggregation (Visor / AutoTempest model) benefits from **salvage/rebuild inventory** alongside retail Craigslist.
- **Region filter** already supports `US`; Copart yards map cleanly to PostGIS via facility lat/lon.
- **Price history** maps to `listing_history` on bid changes and sale resolution.
- **Media-heavy** lots reward a dedicated hydration pipeline (thumbnails in search, full gallery in detail).

Why not scrape blindly:

- Copart has **no documented public developer API** ([catalog status](https://github.com/api-evangelist/copart)).
- Site is login-gated, bot-protected, and ToS-sensitive.
- Plan assumes **read-only aggregation**, outbound links, rate limits, and a **Tier A commercial API** option if self-scrape is blocked.

---

## Access tiers (pick one per phase)

### Tier A — Licensed / aggregator API (preferred for production)

Third-party APIs normalize Copart + often IAAI into JSON. Evaluate during Phase 0:

| Provider | Notes |
|----------|--------|
| [Apibara Vehicle Auction API](https://apibara.tech/en/products/vehicle-auction-data-api/docs) | Copart + IAAI, lot/VIN search, `media`, `condition`, cursor pagination |
| [Carapis Copart](https://www.carapis.com/platforms/global/copart) | Salvage fields: damage, title brand, run/drive, sale history |
| Apify / similar | Scraper-as-a-service; good for spike, costly at scale |

**When to use:** stable ingest without maintaining anti-bot infra; budget for per-lot or monthly cap.

**Integration shape:** `ingestion/copart/client.py` wraps provider HTTP; map their schema → internal `CopartLot` model; store provider raw JSON in `listings.listing.raw_payload`.

### Tier B — Copart web / XHR reverse-engineer (self-hosted)

Discovery spike on [copart.com](https://www.copart.com) logged-out and member sessions:

| Surface | Likely use |
|---------|------------|
| Public search / inventory browse | Paginated lot discovery |
| Lot detail page `…/lot/{lot_number}` | Full specs, gallery JSON, auction state |
| Embedded JSON / `__NEXT_DATA__` / XHR | Structured fields without HTML parse |
| Image CDN URLs | Direct gallery links (see Media hydration) |

**When to use:** no API budget; acceptable maintenance cost; legal review passed.

**Mitigation:** residential/datacenter proxy pool, session rotation, exponential backoff, `metadata.api_usage` tracking, fixture fallback for dev (mirror Craigslist/Yahoo pattern).

### Tier C — Manual / batch import (bootstrap)

- CSV/JSON export from provider trial or one-off scrape
- Seed `notebooks/05_copart_phase0.ipynb` and `ingestion/fixtures/copart_sample.json`
- Unblocks normalize + UI before live ingest

---

## Discovery spike (Phase 0 — 2–3 days)

Before writing production ingest:

1. **Network capture** on Copart: search “Toyota Camry”, open lot detail, image gallery, sale history tab.
2. Log every XHR/fetch: URL, auth cookies, params, response schema, image CDN host patterns.
3. Record **field availability logged-out vs member** (VIN masking, bid amounts, gallery size).
4. Compare **Tier A trial API** response to web capture — pick canonical field mapping.
5. Legal / compliance pass: Copart Terms of Use, robots.txt, CFAA exposure, DMCA/media redistribution.

**Deliverables:**

- `docs/plans/copart-endpoints.json` — endpoint catalog
- `notebooks/05_copart_phase0.ipynb` — live sample + field matrix
- Go/no-go: Tier A vs Tier B for Phase 1

**Expected Copart fields** (from public scraper docs / aggregator schemas):

| Group | Fields |
|-------|--------|
| Identity | `lot_number`, `vin` (may be partial), year, make, model, trim, body_style, color |
| Auction | current_bid, buy_now, auction_date/time, sale_status (upcoming/live/sold/ON_APPROVAL), bid_count |
| Condition | primary_damage, secondary_damage, loss_type, run_and_drive, has_keys, odometer, odometer_brand |
| Title | sale_title_type, title_state, export_eligible |
| Location | yard_name, yard_number, city, state, country, lat, lon |
| Media | thumbnail_url, gallery_urls[], video_url, panorama/360 URL |
| Seller | seller_type (insurance, dealer, etc.) |

---

## Code layout (fits existing packages)

```text
src/notification_rake/ingestion/
  copart/
    __init__.py
    client.py           # httpx / provider wrapper, rate limit, retry
    search.py           # discovery: make/model/year/location filters
    detail.py           # lot detail by lot_number
    normalize.py        # CopartLot → VehicleListing + CopartMeta
    fixtures/           # offline sample lots
  media/
    __init__.py
    hydrate.py          # fetch catalog → store blobs or verify URLs
    storage.py          # local / S3 / MinIO adapter
    thumbnails.py       # primary + card-sized derivatives
  analysis/
    __init__.py
    vin_decode.py       # NHTSA vPIC or cached decode table
    damage.py           # normalize damage codes, severity score
    title_brand.py      # salvage/rebuilt/clean mapping
    specs_extract.py    # engine/trans/drive from structured + title parse

src/notification_rake/workflow/
  copart_pipeline.py    # orchestration (see workflows below)
  jobs/
    copart_discovery.py
    copart_detail_refresh.py
    copart_media_hydrate.py
    copart_metadata_analyze.py
```

Pipeline registration:

```text
workflow/pipeline.py
  → run_copart_pipeline(mode=discovery|detail|media|analyze|full)
  → store_raw_listings()          # source = 'copart'
  → media.hydrate.enqueue()       # async
  → analysis.run()                # async
  → normalize + geocode (yard lat/lon)
  → upsert_listings + Meilisearch sync
```

New `listings.source` row:

| name | country_code | enabled | notes |
|------|--------------|---------|-------|
| `copart` | US | yes | primary US salvage auction |

---

## Data model extensions

### Core listing (existing)

Reuse `VehicleListing` + `listings.listing` with:

- `source` = `copart`
- `source_listing_id` = lot number (string)
- `country` = `US` (yard country; support CA/UK later)
- `vin`, `year`, `mileage`, `price` (current bid or buy-now)
- `latitude` / `longitude` = **yard**, not seller home
- `image_urls` = ordered gallery (URLs or internal paths post-hydration)

### Auction extension (`listings.listing.raw_payload` + typed view)

| Field | Purpose |
|-------|---------|
| `lot_number` | Copart primary key |
| `auction_status` | upcoming / live / sold / on_approval / pure_sale |
| `auction_starts_at` / `auction_ends_at` | UTC |
| `current_bid` / `buy_now_price` / `final_price` | USD |
| `bid_count` | |
| `primary_damage` / `secondary_damage` | normalized enums |
| `loss_type` | collision, theft, flood, hail, … |
| `run_and_drive` | bool |
| `has_keys` | bool |
| `odometer` / `odometer_brand` | EXEMPT, ACTUAL, NOT_ACTUAL |
| `title_type` / `title_state` | salvage, clean, non-repairable |
| `highlights` | Copart feature strings |
| `yard_id` / `yard_name` | |
| `seller_type` | |
| `copart_url` | `https://www.copart.com/lot/{lot_number}` |
| `intended_for_export` | bool when present |

Optional normalized table (Phase 2+):

```sql
-- listings.auction_lot (1:1 with listings.listing for auction sources)
CREATE TABLE listings.auction_lot (
    listing_id UUID PRIMARY KEY REFERENCES listings.listing(id),
    platform TEXT NOT NULL,              -- copart | iaai | yahoo_auctions_jp
    lot_number TEXT NOT NULL,
    auction_status TEXT,
    ends_at TIMESTAMPTZ,
    primary_damage TEXT,
    secondary_damage TEXT,
    loss_type TEXT,
    run_and_drive BOOLEAN,
    has_keys BOOLEAN,
    title_type TEXT,
    UNIQUE (platform, lot_number)
);
```

### Media schema extension (Phase 1b)

Extend `listings.listing_image`:

| Column | Purpose |
|--------|---------|
| `url` | source CDN URL (existing) |
| `position` | gallery order (existing) |
| `storage_path` | local/S3 key after hydration |
| `width` / `height` | pixels |
| `bytes` | size |
| `sha256` | dedupe |
| `hydration_status` | pending / ok / failed / skipped |
| `hydrated_at` | |
| `media_type` | image / video / panorama |
| `is_primary` | card thumbnail |

Optional object store (docker profile):

```text
services:
  minio:   # dev S3-compatible bucket listing-media/
```

Public dashboard serves:

- Search cards → `is_primary` thumbnail (cached)
- Detail modal → full gallery from `storage_path` or signed CDN proxy

---

## Media hydration workflow

Copart galleries often contain **10–30 high-res images** per lot. Hydration is **async** and **idempotent**.

```text
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│ Lot detail  │───▶│ URL catalog  │───▶│ Hydrate worker  │───▶│ Object store │
│ ingest      │    │ listing_image│    │ (queue/job)     │    │ or URL verify│
└─────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
                           │                     │
                           ▼                     ▼
                    metadata.job_runs      thumbnails + sha256 dedupe
```

### Stages

| Stage | Action | Output |
|-------|--------|--------|
| **M0 — Catalog** | Parse gallery URLs from detail JSON/HTML | `listing_image` rows, `hydration_status=pending` |
| **M1 — HEAD verify** | Check URL alive, content-type, content-length | skip dead links; mark failed |
| **M2 — Fetch** | Download to object store (or pass-through if hotlink allowed) | `storage_path`, `sha256`, dimensions |
| **M3 — Derivatives** | Generate card (400px) and detail (1200px) variants | faster dashboard |
| **M4 — Reconcile** | On re-scrape, diff gallery; retire removed images | `deleted_at` soft flag |

### Policies

- **Rate limit:** max N concurrent downloads / yard / minute
- **Dedupe:** sha256 across lots (Copart reuses stock photos rarely; still dedupe)
- **Retention:** keep source URL always; blob optional via `HYDRATE_MEDIA=true`
- **Legal:** prefer **proxy/signed URLs** linking to Copart CDN if redistribution prohibited; full mirror only after legal OK
- **Priority queue:** ending-soon auctions > new today > backlog

### Config

```env
COPART_MEDIA_HYDRATE=true
COPART_MEDIA_STORE=s3          # local | s3 | none
COPART_MEDIA_BUCKET=rake-media
COPART_MEDIA_MAX_PER_LOT=40
COPART_MEDIA_WORKERS=4
```

---

## Metadata analysis workflow

Structured Copart fields feed **search facets** and **buyer risk signals**. Analysis runs after detail ingest (can parallel media).

```text
┌──────────────┐    ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│ Raw lot JSON │───▶│ Normalizers │───▶│ Enrichment jobs  │───▶│ Search index│
└──────────────┘    └─────────────┘    └──────────────────┘    └─────────────┘
                           │                     │
                     damage/title          VIN decode (vPIC)
                     enums + score         make/model verify
```

### Analysis modules

| Module | Input | Output |
|--------|-------|--------|
| **VIN decode** | 17-char VIN (or partial + year/make) | verified make/model/year, body class, engine, fuel, drive |
| **Damage normalize** | `FRONT END`, `Side`, `MINOR DENT/SCRATCHES` | enum + `damage_severity` 1–5 |
| **Title classify** | sale title type + state | `salvage` / `clean` / `non_repairable` badge |
| **Run/drive score** | run_and_drive + keys + damage | `mobility_score` for sort/filter |
| **Odometer trust** | odometer + brand | flag `EXEMPT` / `NOT_ACTUAL` |
| **Market context** | make/model/year/zip | optional comp count from existing `vehicle_listing` retail |
| **Text extract** | title + highlights | tokens for Meilisearch (`copart_damage:front_end`) |

Store analysis output in:

- `listings.listing.raw_payload.analysis` (JSON), and/or
- `metadata.listing_analysis` table if query-heavy

**Buyer-facing derived fields** (public API):

- `damage_badge`, `title_badge`, `runs_and_drives`, `keys_included`
- `vin_decoded_make` (when VIN available)
- `photo_count`, `primary_image_url`

---

## Ingestion workflows (orchestration)

### WF1 — Discovery sweep

**Trigger:** cron daily + hourly delta  
**Input:** search facets (make, model, year range, state, damage type, sale status=upcoming)  
**Steps:**

1. Paginate search results → collect lot numbers
2. Upsert stub raw rows (title, thumb, yard, auction date)
3. Enqueue detail refresh for new/changed lots
4. Update `metadata.crawler_status`

### WF2 — Detail refresh

**Trigger:** queue consumer / job per lot  
**Steps:**

1. Fetch lot detail (Tier A API or web)
2. Merge into `listings.listing` + `listing_history` on price/bid change
3. Diff gallery → update `listing_image` catalog (M0)
4. Enqueue media hydration (M1–M4)
5. Enqueue metadata analysis
6. If sold → write final price event; optionally keep for comps

### WF3 — Live auction poll

**Trigger:** every 1–5 min for lots in `live` state (small subset)  
**Steps:**

1. Refresh current bid + status only (lightweight endpoint)
2. Append `listing_history`
3. Push Gotify alert if saved search match and bid threshold

### WF4 — Public layer sync

**Trigger:** after detail or analysis complete  
**Steps:**

1. `normalize` → `VehicleListing`
2. `geocode` using yard lat/lon (skip Nominatim if coords present)
3. `upsert_listings` → `vehicle_listing.country = US`
4. `sync_documents` → Meilisearch (include damage/title facets as filterable)

### WF5 — End-to-end `copart_full`

Admin action / CLI:

```bash
make run CMD="copart discovery --state CA --limit 500"
make run CMD="copart hydrate --pending"
make run CMD="copart analyze --since 24h"
```

---

## Phases

### Phase 0 — Recon + fixtures (week 1)

- [ ] Discovery spike on [copart.com](https://www.copart.com) + optional Tier A API trial
- [ ] `docs/plans/copart-endpoints.json`
- [ ] `notebooks/05_copart_phase0.ipynb`
- [ ] `ingestion/copart/fixtures/sample_lots.json`
- [ ] Legal review: ToS, media rights, VIN display rules

### Phase 1 — Ingest MVP (week 2–3)

- [ ] `ingestion/copart/{client,search,detail,normalize}.py`
- [ ] `listings.source` row `copart` + migration if needed
- [ ] WF1 discovery + WF2 detail (URLs only, no blob mirror yet)
- [ ] Pipeline branch + admin action `ingest_copart`
- [ ] Dashboard: source tab **Copart**, damage/title badges, auction date
- [ ] Region filter **United States** shows Copart + Craigslist

**Success:** search “Ford F-150” → see Copart lots with yard map pins, thumbnail, current bid.

### Phase 1b — Media hydration (week 4)

- [ ] `ingestion/media/{hydrate,storage,thumbnails}.py`
- [ ] DB migration for extended `listing_image`
- [ ] WF3 hydrate worker (MinIO dev profile)
- [ ] Detail UI: gallery carousel, photo count
- [ ] `hydration_status` metrics in admin

### Phase 2 — Metadata analysis (week 5)

- [ ] `ingestion/analysis/{vin_decode,damage,title_brand}.py`
- [ ] VIN decode via [NHTSA vPIC](https://vpic.nhtsa.dot.gov/api/) with cache
- [ ] Facets: damage type, title type, run/drive, has keys
- [ ] Meilisearch filterable: `primary_damage`, `title_type`, `run_and_drive`

### Phase 3 — Live auction + alerts (week 6–7)

- [ ] WF3 live poll for ending-soon lots
- [ ] Saved search → Gotify on new Copart match / bid drop / ending in 1h
- [ ] Price history chart for bid changes
- [ ] Sort: ending soon, current bid, damage severity

### Phase 4 — Scale + optional IAAI (week 8+)

- [ ] Yard-based geo facets (“within 100 mi of yard”)
- [ ] Sold lot comps (`market_summary` salvage vs retail)
- [ ] Cross-list Copart ↔ retail “similar clean title” (Visor-style)
- [ ] IAAI as `source=iaai` with shared `auction_lot` schema (Apibara covers both)

---

## Ingest schedule

| Job | Cadence | Scope |
|-----|---------|-------|
| `copart_discovery_full` | daily | top makes + nationwide upcoming |
| `copart_discovery_delta` | hourly | new lots, ending &lt;24h |
| `copart_detail_refresh` | 4h | open lots with recent bid activity |
| `copart_live_poll` | 2 min | live auction subset |
| `copart_media_hydrate` | continuous | pending images, priority queue |
| `copart_metadata_analyze` | hourly | lots updated since last run |

Rate budget (self-scrape — tune after spike):

- Discovery: ~500–2k requests/day
- Detail: ~1k lots/day initial backfill, then ~200/day delta
- Media: ~10k image HEAD/GET/day (separate pool)

---

## Dashboard UX (target)

**Search filters (Copart-aware)**

- Region: US (includes Copart + Craigslist)
- Source tab: Copart
- Damage: front, rear, side, hail, flood, …
- Title: salvage, clean, non-repairable
- Runs & drives / keys
- Auction: upcoming, live, buy-it-now
- Sort: ending soon, bid low→high, distance to yard

**Listing card**

```
[photo]  2018 Toyota Camry SE
copart · Lot 12345678 · San Jose, CA yard
Current bid $4,200 · Ends in 6h · Front End damage · Salvage title
Runs & drives · Keys present · 142k mi
```

**Detail view**

- Full gallery (hydrated)
- Damage diagram labels (if available from analysis)
- VIN-decoded specs panel
- Bid / price history
- **Open on Copart** (required outbound link)
- Map: yard location + radius context

---

## Risks

| Risk | Mitigation |
|------|------------|
| No public Copart API | Tier A provider; Tier B scrape with fixtures fallback |
| VIN masked until member | store partial VIN; decode when full VIN available |
| ToS / CFAA / bot blocks | read-only; link out; rate limits; legal review |
| Media redistribution | default hotlink + proxy; mirror only if permitted |
| Gallery URL expiry | re-fetch detail on 403; store sha256 not just URL |
| Salvage vs retail price compare | separate badges; don’t mix “good deal” scores |
| IAAI overlap | defer IAAI; don’t dedupe by VIN across platforms until crosswalk exists |
| Meilisearch geo | index yard `_geo`; filter with existing radius search |

---

## Config additions

```env
# Copart ingest
COPART_ENABLED=true
COPART_API_MODE=auto              # provider | web | auto
COPART_API_BASE=                  # Tier A provider base URL
COPART_API_KEY=
COPART_WEB_BASE=https://www.copart.com
COPART_INGEST_PAGE_SIZE=100
COPART_REQUESTS_PER_DAY=5000
COPART_DEFAULT_COUNTRY=US

# Media hydration
COPART_MEDIA_HYDRATE=true
COPART_MEDIA_STORE=local          # local | s3 | none
COPART_MEDIA_MAX_PER_LOT=40

# Analysis
COPART_VIN_DECODE=true
NHTSA_VPIC_URL=https://vpic.nhtsa.dot.gov/api
```

---

## Immediate next steps

1. Run **Phase 0 discovery spike** → `copart-endpoints.json` + notebook.
2. Trial **Tier A API** (Apibara/Carapis) vs captured XHR — pick ingest path.
3. Add **`copart` source row** + fixture-driven normalize tests.
4. Implement **`ingestion/copart/search.py`** + **`detail.py`** (provider or fixture).
5. Wire **WF1/WF2** into pipeline; dashboard Copart tab + damage badges.
6. Design **media migration** (`listing_image` extensions) before hydration worker.
7. Schedule **legal review** before production scrape or CDN mirroring.

After Phase 1 ships, media hydration and metadata analysis layer on without changing the canonical lot model — same pattern as Yahoo detail enrich + proxy quotes.

---

## Related docs

- [Yahoo proxy ingestion](yahoo-proxy-ingestion.md) — auction source template
- [Ingestion-Pipeline](../wiki/Ingestion-Pipeline.md) — existing workflow
- [Dashboard-and-Search](../wiki/Dashboard-and-Search.md) — region + source tabs
- [Architecture](../wiki/Architecture.md) — `listings` vs `public` layers

# Yahoo Auctions + proxy ingestion plan

Goal: ingest **all Yahoo Auctions Japan vehicle listings** (primary source), then overlay **Buyee / Neokyo / FromJapan** proxy fees and shipping so buyers can search once and compare landed cost.

References: [Yahoo Auctions 中古車・新車](https://auctions.yahoo.co.jp/category/list/26360/), [Buyee](https://buyee.jp/), [Neokyo](https://neokyo.com/), [FromJapan](https://www.fromjapan.co.jp/), [Yahoo Auction Search API v2](http://auctions.yahooapis.jp/AuctionWebService/V2/search) (official docs: [developer.yahoo.co.jp](https://developer.yahoo.co.jp/webapi/auctions/)).

---

## Strategy

**One canonical listing per Yahoo auction ID.** Proxies are not separate inventory — they are purchase/shipping channels on top of the same `auction_id`.

```text
Yahoo Auctions JP (source of truth)
  → search + detail ingest
  → normalize to VehicleListing + auction extensions
  → public search UI

Proxy layer (phase 2+)
  → fee rules + shipping estimates per proxy
  → compare panel on listing detail
```

Why Yahoo first, proxies second:

- [Buyee](https://buyee.jp/), [Neokyo](https://neokyo.com/blog/what-is-yahoo-auctions/), and FromJapan all surface **the same Yahoo listings** with markup, service fees, and international shipping — not independent catalogs.
- Proxy sites rarely expose stable public APIs; their search UIs call Yahoo (directly or via server-side proxy). Reverse-engineering three proxies for search duplicates work Yahoo already provides.
- Proxy value for this product is **landed-cost comparison**, not discovery.

---

## Yahoo endpoints (primary)

### Tier A — Official Search API (preferred for bulk ingest)

| Endpoint | Use |
|----------|-----|
| `GET http://auctions.yahooapis.jp/AuctionWebService/V2/search` | Paginated search (50/page) |
| `GET .../V2/auctionItem` | Single auction detail |
| `GET .../V2/sellingList` | Seller history (optional) |

Required: Yahoo Developer **Application ID** (`appid`). Register at [Yahoo Developer Network](https://developer.yahoo.co.jp/). Documented limit ~**50,000 calls/day** per app.

Key params for vehicles:

| Param | Value / notes |
|-------|----------------|
| `category` / `auccat` | `26360` = 中古車・新車 (~47k listings). Parent `26318` = all auto/moto |
| `query` | Make/model JP keywords (トヨタ スープラ, 日産 スカイライン) |
| `aucminprice` / `aucmaxprice` | JPY bid range |
| `loc_code` | Prefecture 1–48 (Hokkaido → overseas) |
| `sort` / `order` | `cbids`, `end`, `bids`, etc. |
| `page` | 1-based pagination |

Also track subcategories for completeness:

- `26360` — used/new car bodies (main target)
- Parts cars, kei, trucks, campers — separate `auccat` under [26318 tree](https://auctions.yahoo.co.jp/list1/26318-category.html)

### Tier B — Web fallback (if appid blocked or fields missing)

| Endpoint | Use |
|----------|-----|
| `GET https://auctions.yahoo.co.jp/search/search` | HTML search (params: `p`, `auccat`, `aucminprice`, `aucmaxprice`, `b`, `n`) |
| `GET https://auctions.yahoo.co.jp/category/list/26360/` | Category browse with car-specific sorts (mileage, year) |
| `GET https://page.auctions.yahoo.co.jp/jp/auction/{id}` | Detail page (structured fields in HTML/embedded JSON) |

Use Tier B only where official API lacks vehicle-specific attributes (structured year, mileage, inspection expiry, body type). Car category uses **dedicated listing schema** per [Yahoo car listing guide](https://auctions.yahoo.co.jp/car/guide/carguide/sell/).

### Tier C — Authenticated APIs (later, optional)

OAuth endpoints (`myWonList`, bidding) need [YConnect](https://developer.yahoo.co.jp/yconnect/v2/). Out of scope for read-only aggregator unless you add bid-on-behalf features.

---

## Discovery spike (1–2 days, do first)

Before writing ingest code, capture live traffic from each proxy on a **vehicle search**:

1. Open DevTools → Network on Buyee, Neokyo, FromJapan Yahoo auction search tabs.
2. Search `スカイライン` with `auccat=26360`.
3. Log every XHR/fetch: URL, params, response shape, auth headers, rate limits.
4. Confirm all three resolve to Yahoo auction IDs (same `AuctionID` / URL pattern).

Deliverable: `docs/plans/yahoo-proxy-endpoints.json` — endpoint catalog for implementation.

Expected findings:

- Search → Yahoo API or Yahoo HTML parse on proxy backend
- Item detail → `page.auctions.yahoo.co.jp/jp/auction/{id}` wrapper
- Shipping → proxy-specific calculator (likely form POST or internal REST); **no public docs** for Buyee/Neokyo/FromJapan ([Buyee shipping tool](https://buyee.jp/helpcenter/guide/shipping-fees) is browser-only)

Tools: browser DevTools, [peek-api](https://github.com/alexknowshtml/peek-api), or a one-off Playwright script in `notebooks/04_yahoo_proxy_recon.ipynb`.

---

## Code layout (fits existing packages)

```text
src/notification_rake/ingestion/
  yahoo/
    __init__.py
    client.py          # httpx wrapper, appid, rate limit, retry
    search.py          # search API + pagination
    detail.py          # auctionItem + HTML fallback
    categories.py      # auccat constants, brand_id map
    normalize.py       # Yahoo item → VehicleListing + AuctionMeta
  proxy/
    __init__.py
    base.py            # ProxyQuoteProvider protocol
    buyee.py
    neokyo.py
    fromjapan.py
    fees.yaml          # static fee tables until calculators reverse-engineered
```

Pipeline addition:

```text
workflow/pipeline.py
  → ingest_yahoo_vehicles()   # new source: listings.source = 'yahoo_auctions_jp'
  → store_raw_listings()
  → normalize (JP make/model catalog extension)
  → upsert (geom = prefecture centroid from loc_code)
```

New `listings.source` rows:

| name | enabled | notes |
|------|---------|-------|
| `yahoo_auctions_jp` | yes | primary |
| `buyee` | no | quote overlay only, not duplicate listings |
| `neokyo` | no | quote overlay |
| `fromjapan` | no | quote overlay |

---

## Data model extensions

### `VehicleListing` (or sibling `AuctionListing`)

Add optional auction fields (JSON column or `listings.listing.raw_payload`):

| Field | Source |
|-------|--------|
| `currency` | always `JPY` for Yahoo |
| `buyout_price` | 即決 |
| `current_bid` | 現在価格 |
| `bid_count` | |
| `ends_at` | auction end UTC |
| `prefecture_code` | Yahoo `loc_code` |
| `condition` | 新車/中古/… |
| `inspection_expiry` | 車検 |
| `body_type` | kei, sedan, etc. |
| `source_url` | `https://page.auctions.yahoo.co.jp/jp/auction/{id}` |
| `proxy_links` | `{buyee, neokyo, fromjapan}` deep links |

Keep `source_listing_id` = Yahoo auction ID (e.g. `v1234567890`).

### New schema: `reference.proxy_provider`

| Column | Purpose |
|--------|---------|
| `name` | buyee, neokyo, fromjapan |
| `service_fee_pct` | e.g. Buyee ~300–500 JPY + % |
| `payment_fee_pct` | |
| `domestic_shipping_default` | seller → proxy warehouse estimate |
| `intl_shipping_rules` | JSON by country/weight/method |
| `updated_at` | manual or scraped refresh |

### New schema: `listings.proxy_quote`

Per listing × proxy × destination country:

| Column | Purpose |
|--------|---------|
| `listing_id` | FK |
| `proxy` | buyee / neokyo / fromjapan |
| `destination_country` | ISO |
| `item_price_jpy` | bid or buyout |
| `service_fee_jpy` | |
| `domestic_ship_jpy` | |
| `intl_ship_jpy` | estimate |
| `total_landed_jpy` | sum |
| `total_landed_usd` | FX snapshot |
| `confidence` | exact / estimated / stale |
| `quoted_at` | |

---

## Phases

### Phase 0 — Recon + Yahoo appid (week 1)

- [ ] Register Yahoo Developer app, store `YAHOO_APP_ID` in config — see [`docs/yahoo-setup.md`](../yahoo-setup.md)
- [ ] Network capture on Buyee / Neokyo / FromJapan (vehicle search + item page + shipping calculator)
- [ ] Notebook: [`notebooks/04_yahoo_phase0.ipynb`](../../notebooks/04_yahoo_phase0.ipynb) — prove search `auccat=26360`, map fields
- [ ] Legal review: Yahoo [API terms](https://developer.yahoo.co.jp/), robots.txt, rate limits; proxies' ToS for calculator automation

### Phase 1 — Yahoo vehicle ingest MVP (week 2–3)

- [ ] `ingestion/yahoo/client.py` — search API with pagination, exponential backoff, `metadata.api_usage` tracking
- [ ] Category sweep job: full `26360` index on schedule (respect 50k/day cap — ~950 pages × 50 = full category in one day if needed)
- [ ] Detail enrich: auctionItem API for price, images, end time, seller
- [ ] Normalize JP titles → make/model (extend `transform/normalize.py` with JP catalog: トヨタ→Toyota, etc.)
- [ ] Geocode via prefecture centroid (not lat/lon from listing — cars rarely have coords)
- [ ] Admin: enable `yahoo_auctions_jp` source, pipeline action `ingest_yahoo`
- [ ] Dashboard: source tab "Yahoo JP", currency JPY, auction countdown, bid count badge

**MVP success:** search "スカイライン" or filter Toyota → see live Yahoo vehicle auctions with price history on re-scrape.

### Phase 2 — Detail + history (week 4)

- [ ] Poll open auctions every N hours; write `listing_history` on bid/price change
- [ ] Parse car-specific detail page fields (mileage, year, 車台番号 last-3, inspection)
- [ ] Completed auction ingest (`search` with closed filter or sold HTML) for market stats
- [ ] `market_summary` by make/model in JPY

### Phase 3 — Proxy quote overlay (week 5–7)

- [ ] Static fee tables from published proxy pricing pages
- [ ] Reverse-engineer calculator endpoints (discovery spike output)
- [ ] `proxy_quote` job: for each active listing, compute Buyee / Neokyo / FromJapan landed estimate for `DEFAULT_DEST_COUNTRY` (US)
- [ ] Listing detail UI: **Compare proxies** table — item + service + domestic + intl = total
- [ ] Deep links: "Open in Buyee", "Open in Neokyo", "Open in FromJapan"

**Car-specific shipping note:** whole vehicles usually **cannot** ship internationally via standard parcel proxies (weight/size limits on [Buyee EMS/FedEx](https://buyee.jp/helpcenter/guide/shipping-method)). Plan must distinguish:

- **Exportable parts / kei / motorcycles** — proxy shipping estimates apply
- **Full car bodies** — likely **domestic Japan only**; show proxy comparison for **bid service fee + domestic delivery to port/dealer**, flag "intl roll-on container — quote separately"

This honesty filter prevents bogus $200 EMS quotes on a 1500kg sedan.

### Phase 4 — Unified search UX (week 8+)

- [ ] Single search bar: EN query → auto-translate to JP for Yahoo API (`query` param)
- [ ] Source facet: US (Craigslist) + JP (Yahoo) side by side
- [ ] Saved search alerts on new Yahoo matches (Gotify)
- [ ] FX rate feed for USD/EUR display
- [ ] Optional: proxy preference profile ("I always use Neokyo") → sort by that landed total

---

## Ingest schedule

| Job | Cadence | Scope |
|-----|---------|-------|
| `yahoo_full_sweep` | daily | all `26360` pages (or delta if API supports) |
| `yahoo_hot_delta` | hourly | ending-soon (<24h), new today, watched makes |
| `yahoo_detail_refresh` | 4h | open listings with bid activity |
| `proxy_quote_refresh` | daily | active listings × 3 proxies |

Rate budget (50k/day official API):

- Full sweep ~950 pages = ~950 calls (search only)
- Detail enrich 5k listings = 5k calls
- Headroom for search UX live queries

---

## Dashboard UX (target)

**Search page**

- Region toggle: US / Japan / All
- JP filters: make (JP+EN), year, mileage, prefecture, price JPY, ending within
- Sort: ending soon, price, bids, newest

**Listing detail**

```
[photos]  1999 Nissan Skyline GT-R
Yahoo auction v1234…  ·  ends in 2d 4h  ·  現在 1,200,000 JPY  ·  12 bids

Specs: year, mileage, inspection, prefecture …
Price history chart (from listing_history)

Compare purchase proxies (est. to USA)
┌──────────┬─────────┬─────────┬─────────┬─────────┐
│ Proxy    │ Service │ Domestic│ Intl*   │ Total   │
├──────────┼─────────┼─────────┼─────────┼─────────┤
│ Buyee    │ ¥…      │ ¥…      │ n/a †   │ ¥…      │
│ Neokyo   │ …       │ …       │ …       │ …       │
│ FromJapan│ …       │ …       │ …       │ …       │
└──────────┴─────────┴─────────┴─────────┴─────────┘
† Full vehicle — international parcel not available; domestic to port only

[Open on Yahoo] [Open via Buyee] [Open via Neokyo] [Open via FromJapan]
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| Yahoo API appid denial or throttle | HTML fallback; cache aggressively |
| Proxy calculator changes | versioned `fees.yaml`; stale quote badge |
| Full car intl shipping nonsense | vehicle class flag; don't quote EMS for 4-door sedan |
| JP make/model normalization gaps | seed `reference` catalog from Yahoo `brand_id` list |
| Legal / ToS | read-only aggregation; link out for purchase; no bid automation v1 |
| Language | store raw JP title; display EN via optional translation layer |

---

## Config additions

```env
YAHOO_APP_ID=
YAHOO_AUCTION_BASE=https://auctions.yahooapis.jp/AuctionWebService/V2
YAHOO_VEHICLE_AUCCAT=26360
YAHOO_INGEST_PAGE_SIZE=50
YAHOO_REQUESTS_PER_DAY=45000
DEFAULT_DEST_COUNTRY=US
FX_USD_JPY=150.0   # or live feed
```

---

## Immediate next steps

1. Run **Phase 0 discovery spike** (notebook + endpoint JSON).
2. Apply for **Yahoo Developer appid**.
3. Implement **`ingestion/yahoo/search.py`** against official V2 search with `auccat=26360`.
4. Add **`yahoo_auctions_jp`** source row + pipeline branch.
5. Extend dashboard with JP source tab and JPY formatting.

After Phase 1 ships, proxy comparison becomes a **quote layer** on existing listings — not a second scrape of three sites.

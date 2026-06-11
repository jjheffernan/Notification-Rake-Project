# Yahoo Auctions JP — setup guide

Wiki: [Yahoo-Auctions-JP](wiki/Yahoo-Auctions-JP.md). Roadmap: [`plans/yahoo-proxy-ingestion.md`](plans/yahoo-proxy-ingestion.md).

Buyee, Neokyo, and FromJapan all surface the **same Yahoo listings** — Yahoo is the canonical source; proxies are fee/shipping overlays (phase 3).

---

## Prerequisites

- Python env: `make install` or `pip install -e ".[dev]"`
- Jupyter (optional): `make jupyter` or local `jupyter lab notebooks/`
- Outbound HTTPS from your machine or Docker `app` container

---

## 1. Yahoo Developer Application ID

1. Create a Yahoo Japan ID if needed.
2. Open [Yahoo Developer Network](https://developer.yahoo.co.jp/).
3. Register a new application (Web service / オークション API).
4. Copy the **Application ID** (`appid`).

Official API docs (Japanese): [Auction Search v2](https://developer.yahoo.co.jp/webapi/auctions/auction/v2/search.html).

Rate limit: about **50,000 requests/day** per appid. Plan bulk sweeps accordingly.

---

## 2. Environment variables

Add to `.env` (see `.env.example`):

```env
YAHOO_APP_ID=your-application-id-here
YAHOO_AUCTION_API_BASE=https://auctions.yahooapis.jp/AuctionWebService/V2
YAHOO_VEHICLE_AUCCAT=26360
YAHOO_INGEST_PAGE_SIZE=50
YAHOO_REQUESTS_PER_DAY=45000
DEFAULT_DEST_COUNTRY=US
FX_USD_JPY=150.0
```

| Variable | Purpose |
|----------|---------|
| `YAHOO_APP_ID` | Required for live API calls |
| `YAHOO_VEHICLE_AUCCAT` | `26360` = 中古車・新車 ([category list](https://auctions.yahoo.co.jp/category/list/26360/)) |
| `YAHOO_INGEST_PAGE_SIZE` | Max 50 per search page |
| `YAHOO_REQUESTS_PER_DAY` | Soft cap enforced in client (leave headroom below 50k) |

Without `YAHOO_APP_ID`, the client returns bundled **sample JSON** (same pattern as Craigslist RSS fallback).

---

## 3. Python client (phase 0)

```text
src/notification_rake/ingestion/yahoo/
  client.py       — httpx, appid, rate budget, JSON parse
  categories.py   — auccat constants, proxy deep links
  search.py       — search + pagination helpers
```

Quick test:

```python
from notification_rake.ingestion.yahoo import search_vehicle_auctions

result = search_vehicle_auctions(query="スカイライン", page=1)
print(result.total_available, len(result.items))
for hit in result.items[:3]:
    print(hit.auction_id, hit.title, hit.current_price_jpy)
```

CLI-style from repo root:

```bash
python -c "
from notification_rake.ingestion.yahoo import search_vehicle_auctions
r = search_vehicle_auctions(query='トヨタ', page=1)
print(r.total_available, [i.title for i in r.items[:2]])
"
```

---

## 4. Phase 0 notebook

Run [`notebooks/04_yahoo_phase0.ipynb`](../notebooks/04_yahoo_phase0.ipynb):

1. Verify `YAHOO_APP_ID` is loaded
2. Search `auccat=26360` and inspect field mapping
3. Paginate first 3 pages (rate-aware)
4. Proxy recon checklist (Buyee / Neokyo / FromJapan DevTools steps)
5. Optional: write discovered endpoints to `docs/plans/yahoo-proxy-endpoints.json`

```bash
make jupyter
# open http://127.0.0.1:8888 → notebooks/04_yahoo_phase0.ipynb
```

---

## 5. Primary API endpoints

### Search (bulk ingest)

```http
GET https://auctions.yahooapis.jp/AuctionWebService/V2/search
  ?appid={YAHOO_APP_ID}
  &query={utf8_keywords}
  &category=26360
  &page=1
  &results=50
  &output=json
```

Common params:

| Param | Example | Notes |
|-------|---------|-------|
| `category` | `26360` | Used/new car bodies |
| `query` | `日産 スカイライン` | UTF-8 keywords |
| `aucminprice` / `aucmaxprice` | `500000` | JPY |
| `loc_code` | `13` | Prefecture (13 = Tokyo) |
| `sort` | `cbids`, `end`, `bids` | Price, end time, bid count |
| `order` | `a`, `d` | Asc / desc |

### Item detail (phase 1)

```http
GET .../V2/auctionItem?appid=...&auctionID=v1234567890&output=json
```

### Web fallback (no appid / extra car fields)

| URL | Use |
|-----|-----|
| `https://auctions.yahoo.co.jp/category/list/26360/` | HTML category browse |
| `https://page.auctions.yahoo.co.jp/jp/auction/{id}` | Detail page |

---

## 6. Proxy recon (manual, phase 0)

For each proxy, capture Network → Fetch/XHR while searching **スカイライン** in Yahoo auctions (vehicles):

| Site | Start URL |
|------|-----------|
| [Buyee](https://buyee.jp/) | Yahoo Auctions tab |
| [Neokyo](https://neokyo.com/) | Search → Yahoo Auctions |
| [FromJapan](https://www.fromjapan.co.jp/) | Auction search |

Record per request:

- URL and HTTP method
- Query/body params
- Whether response contains Yahoo `AuctionID`
- Auth headers / cookies required

Save findings in `docs/plans/yahoo-proxy-endpoints.json`:

```json
{
  "captured_at": "2026-06-24",
  "proxies": {
    "buyee": { "search": [], "detail": [], "shipping": [] },
    "neokyo": { "search": [], "detail": [], "shipping": [] },
    "fromjapan": { "search": [], "detail": [], "shipping": [] }
  }
}
```

---

## 7. Vehicle shipping caveat

Full car bodies usually **cannot** use standard parcel international shipping (EMS/FedEx size/weight limits). See [Buyee shipping methods](https://buyee.jp/helpcenter/guide/shipping-method).

Phase 3 proxy quotes must flag:

- **Parcel-eligible** — parts, small items, some bikes
- **Domestic / export only** — full vehicles → bid fee + domestic leg; intl container quoted separately

---

## 8. Tests

```bash
make test   # includes tests/test_yahoo_client.py (fixture-backed)
```

---

## 9. Next phases

| Phase | Deliverable |
|-------|-------------|
| 0 | Appid, client, notebook, proxy endpoint JSON |
| 1 | Pipeline ingest → `listings.source = yahoo_auctions_jp`, dashboard JP tab |
| 2 | Bid polling, price history, sold comps |
| 3 | Buyee / Neokyo / FromJapan landed-cost overlay |
| 4 | Unified EN/JP search + alerts |

See [`plans/yahoo-proxy-ingestion.md`](plans/yahoo-proxy-ingestion.md) for schema and schedule details.

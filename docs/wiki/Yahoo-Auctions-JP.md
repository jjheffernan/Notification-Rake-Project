# Yahoo Auctions JP

Japan used-car auctions via Yahoo (JDirectItems). Buyee, Neokyo, and FromJapan wrap the **same Yahoo listings** — Yahoo is canonical; proxies are fee/shipping overlays (later phase).

## Phase status

| Phase | Status | Deliverable |
|-------|--------|-------------|
| 0 | **Done** | Client, fixture, notebook, setup guide |
| 1 | Planned | Pipeline ingest → `yahoo_auctions_jp` source |
| 2 | Planned | Bid polling, sold comps |
| 3 | Planned | Buyee / Neokyo / FromJapan landed-cost UI |
| 4 | Planned | Unified EN/JP search + alerts |

## Setup

1. Register [Yahoo Developer Application ID](https://developer.yahoo.co.jp/)
2. Set `YAHOO_APP_ID` in `.env`
3. Run notebook `04_yahoo_phase0.ipynb`

Detailed steps: repo file `docs/yahoo-setup.md` (same content as this page's source).

## Primary API

```http
GET https://auctions.yahooapis.jp/AuctionWebService/V2/search
  ?appid={YAHOO_APP_ID}
  &category=26360
  &query={keywords}
  &page=1
  &results=50
  &output=json
```

| Category ID | Meaning |
|-------------|---------|
| `26360` | 中古車・新車 (used/new car bodies) |
| `26318` | 自動車、オートバイ (parent) |

Rate limit: ~50,000 requests/day per appid.

## Python client

```text
ingestion/yahoo/
  client.py      — YahooClient, rate budget, JSON/JSONP
  search.py      — search_vehicle_auctions(), YahooAuctionHit
  categories.py  — auccat constants, proxy deep links
```

```python
from notification_rake.ingestion.yahoo import search_vehicle_auctions

result = search_vehicle_auctions(query="スカイライン", page=1)
for hit in result.items:
    print(hit.auction_id, hit.title, hit.current_price_jpy)
```

No appid → bundled fixture (`fixtures/yahoo_vehicle_search_sample.json`).

## Proxy recon (phase 0 manual)

Capture DevTools network traffic on Buyee, Neokyo, FromJapan while searching vehicles. Record endpoints in `docs/plans/yahoo-proxy-endpoints.json`.

## Vehicle shipping caveat

Full car bodies usually **cannot** ship international parcel (EMS/FedEx limits). Phase 3 quotes must distinguish parcel-eligible items vs domestic/export-only vehicles.

## Full roadmap

Repo: `docs/plans/yahoo-proxy-ingestion.md`

## Related

- [Ingestion-Pipeline](Ingestion-Pipeline)
- [Configuration](Configuration)

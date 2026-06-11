# EU Marketplaces (UK & Germany)

Notification Rake aggregates classified and auction listings from major European vehicle marketplaces alongside US/JP sources.

## United Kingdom (GB)

| Source | Site | Type | Similar to |
|--------|------|------|------------|
| `ebay_uk` | [eBay UK](https://www.ebay.co.uk) | Classified/auction | eBay US |
| `gumtree` | [Gumtree](https://www.gumtree.com) | Classified | Craigslist |
| `autoscout24_uk` | [AutoScout24 UK](https://www.autoscout24.co.uk) | Dealer/classified | AutoTrader |
| `copart_uk` | [Copart UK](https://www.copart.co.uk) | Salvage auction | Copart US |

## Germany (DE)

| Source | Site | Type | Similar to |
|--------|------|------|------------|
| `mobile_de` | [mobile.de](https://www.mobile.de) | Classified | Craigslist / AutoTrader |
| `autoscout24_de` | [AutoScout24 DE](https://www.autoscout24.de) | Dealer/classified | AutoScout24 UK |
| `ebay_de` | [eBay DE Motors](https://www.ebay.de) | Classified/auction | eBay US |
| `copart_de` | [Copart DE](https://www.copart.de) | Salvage auction | Copart US |

## Ingestion

- **Bulk pipeline**: `ingest_all` includes EU fixtures when `EU_MARKETPLACES_ENABLED=true`
- **Admin action**: `ingest_europe`
- **Connected accounts**: link any EU provider via the dashboard panel

Fixture mode ships sample listings in `fixtures/eu_marketplaces_sample.json`. Live API/RSS wiring follows the same connector pattern as eBay and Copart.

## Region filter

Dashboard region dropdown includes **United Kingdom** and **Germany**. Filter by `country=GB` or `country=DE` to focus on EU listings.

## Import rules

When browsing JP/EU/US inventory for cross-border purchase, enable:

- **US import eligible (25+ yr rule)** — model year ≤ current year − 25
- **Canada import eligible (15+ yr rule)** — model year ≤ current year − 15

Eligible listings show badges on cards and in detail view. Both toggles active shows the union (15+ year threshold).

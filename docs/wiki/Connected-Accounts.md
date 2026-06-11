# Connected accounts

Buyers can link marketplace accounts to augment unified search — no site login required; a browser **profile ID** scopes credentials.

## Supported providers

| Provider | Config keys | Behavior |
|----------|-------------|----------|
| `craigslist` | `rss_url` | Saved search RSS feed |
| `yahoo_auctions_jp` | `query`, `max_pages` | Yahoo Auctions search |
| `buyee` | `query`, `watchlist_query`, `member_id` | Yahoo search + Buyee metadata |
| `ebay` | `api_key` or `oauth_token`, `query` | eBay Browse API (fixture if unset) |
| `copart` | `query`, `state`, `limit` | Copart lot search |

## API

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/profile` | Create anonymous profile UUID |
| GET | `/api/accounts?profile_id=` | List connected accounts |
| POST | `/api/accounts` | Connect / update account |
| DELETE | `/api/accounts/{id}?profile_id=` | Disconnect |
| POST | `/api/accounts/sync` | Pull listings from all enabled accounts |

Credentials are stored in `metadata.connected_account` (JSON config). Use env-appropriate encryption for production.

## UI

Use the **Connected accounts** nav link (`/accounts`) to connect providers, sync watchlists, and review connection status.

Example Craigslist connector:

```json
{"rss_url": "https://sfbay.craigslist.org/search/cta?format=rss&query=toyota+camry"}
```

## Admin actions

- `ingest_all` — Craigslist + Yahoo + Copart
- `ingest_copart` / `ingest_yahoo` — single source
- `search_reindex` — Meilisearch full sync

## Related

- [Copart-Auctions](Copart-Auctions)
- [Yahoo-Auctions-JP](Yahoo-Auctions-JP)
- [Ingestion-Pipeline](Ingestion-Pipeline)

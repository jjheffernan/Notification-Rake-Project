# Connected accounts

Buyers can link marketplace accounts to augment unified search. Credentials are scoped to a **profile UUID** — separate from operator admin login.

## Buyer authentication

Notification Rake has two auth surfaces (see [Configuration](Configuration#dashboard-auth-and-admin) and [`SECURITY.md`](../../SECURITY.md)):

| Actor | Entry | Identity |
|-------|-------|----------|
| **Buyer** | `/signin` | Profile UUID created or restored client-side |
| **Operator** | `/admin/login` | `ADMIN_USER` / `ADMIN_PASSWORD` session — not linked from public nav when `ADMIN_NAV_VISIBLE=false` (default) |

**Sign in before private features.** Visit `/signin` to create a new profile (`POST /api/profile`) or paste an existing UUID. The ID is stored in browser `localStorage` (`rake_profile_id`) and sent as `profile_id` on API calls. Nav links to **Connected accounts** (`/accounts`) and **Watchlist** (`/watchlist`) redirect unsigned buyers to `/signin`.

Treat the profile UUID like a password — it is a bearer token; anyone with the UUID can act as that profile. Do not share URLs that embed `profile_id`.

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

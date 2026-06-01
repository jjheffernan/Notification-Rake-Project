# Notification Rake

Vehicle listing aggregation, geospatial search, and availability notifications. Buyer-first — unified search, map, price history, multi-source tabs.

Architecture: [`specs.md`](specs.md). **Full docs:** [`docs/wiki/Home.md`](docs/wiki/Home.md) (GitHub Wiki–ready).

## MVP stack

PostGIS (layered schemas) + Flask dashboard + Hasura GraphQL + Gotify + Jupyter.

| Layer | Tool |
|-------|------|
| Search | PostGIS `vehicle_listing` + Python `search` module |
| Raw listings | `listings` schema |
| Reference catalog | `reference` schema |
| Operations | `metadata` schema + Grafana/Prometheus |
| Analytics | Metabase |
| DB admin | Adminer |
| Public UI | Flask + Leaflet at `:8000` (split map + list) |
| Admin UI | `/admin` session login |
| Ingest (live) | Craigslist RSS |
| Ingest (phase 0) | Yahoo Auctions JP client |

## Quick start

```bash
cp .env.example .env
docker compose up -d
docker compose --profile dev-tools up -d jupyter adminer metabase grafana prometheus
make run CMD=pipeline
make test
```

- **Search:** http://127.0.0.1:8000
- **Admin:** http://127.0.0.1:8000/admin/login (`ADMIN_USER` / `ADMIN_PASSWORD`)

## Documentation

| Doc | Content |
|-----|---------|
| [**Wiki (GitHub-ready)**](docs/wiki/Home.md) | Full documentation set + `_Sidebar.md` |
| [`docs/README.md`](docs/README.md) | How to sync wiki ↔ repo |
| [`docs/architecture.md`](docs/architecture.md) | Schemas, packages, services |
| [`docs/functions.md`](docs/functions.md) | Module reference |
| [`docs/yahoo-setup.md`](docs/yahoo-setup.md) | Yahoo Auctions JP setup |
| [`docs/deploy.md`](docs/deploy.md) | Coolify / CI |
| [`docs/audit.md`](docs/audit.md) | Audit notes |
| [`specs.md`](specs.md) | Product spec |
| [`SECURITY.md`](SECURITY.md) | Secrets checklist |

## Agent skills

`.agent/` — run `make install-skills`. `/caveman`, `/ponytail` in Cursor.

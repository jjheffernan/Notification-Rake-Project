# Notification Rake

Self-hosted vehicle market aggregator. Buyer-first search across ingested sources — map, filters, price history, alerts.

Inspired by [Visor](https://visor.vin/) and [AutoTempest](https://www.autotempest.com/).

## What it does

1. **Ingest** listings (Craigslist RSS today; Yahoo Auctions JP in progress)
2. **Normalize** make/model against a Postgres catalog
3. **Geocode** listings (Nominatim + region centroids)
4. **Index** into PostGIS for radius search
5. **Search** via public dashboard (no login) or REST API
6. **Alert** on new matches via Gotify
7. **Operate** via admin console (pipeline, health, sources)

## Stack (MVP)

| Layer | Technology |
|-------|------------|
| Database | PostGIS (layered schemas) |
| Search API | Python `search` module + REST |
| GraphQL | Hasura (admin secret) |
| Public UI | Flask + Leaflet map (`gunicorn`) |
| Admin UI | Flask `/admin` session auth |
| Notifications | Gotify |
| CLI | `python -m notification_rake <cmd>` |
| Notebooks | JupyterLab (dev-tools profile) |
| Analytics | Metabase, Grafana, Prometheus (dev-tools) |

## Quick start

```bash
cp .env.example .env
docker compose up -d
docker compose --profile dev-tools up -d jupyter adminer metabase grafana prometheus
make run CMD=pipeline
```

Open **http://127.0.0.1:8000** — public search with split map + list view.

Admin: **http://127.0.0.1:8000/admin/login** (`ADMIN_USER` / `ADMIN_PASSWORD` in `.env`).

## Documentation index

| Page | Topic |
|------|--------|
| [Setup-and-Quick-Start](Setup-and-Quick-Start) | Install, compose, Makefile |
| [Architecture](Architecture) | Schemas, packages, services |
| [Configuration](Configuration) | Environment variables |
| [Dashboard-and-Search](Dashboard-and-Search) | Public UI, map, filters, API |
| [Admin-Console](Admin-Console) | Ops UI, pipeline actions |
| [Ingestion-Pipeline](Ingestion-Pipeline) | Craigslist, workflow, scripts |
| [Yahoo-Auctions-JP](Yahoo-Auctions-JP) | Phase 0 Yahoo client + proxy plan |
| [API-Reference](API-Reference) | REST endpoints, GraphQL |
| [Development](Development) | Tests, lint, notebooks |
| [Deployment](Deployment) | Coolify, CI/CD |

Product spec (repo root): [specs.md](https://github.com/jjheffernan/Notification-Rake-Project/blob/main/specs.md)

## Publishing to GitHub Wiki

This folder (`docs/wiki/`) is formatted for [GitHub Wiki](https://docs.github.com/en/communities/documenting-your-project-with-wikis):

1. Enable Wiki on the repository.
2. Clone the wiki git repo: `git clone https://github.com/<owner>/<repo>.wiki.git`
3. Copy `docs/wiki/*.md` into the wiki clone (keep `_Sidebar.md`).
4. Commit and push.

Cross-links use `[Page-Name](Page-Name)` (no `.md` extension) — valid in GitHub Wiki.

# Setup and Quick Start

## Requirements

- Docker + Docker Compose
- Python 3.12+ (local tests/notebooks)
- Copy of `.env` from `.env.example`

## Core services

```bash
cp .env.example .env
docker compose up -d          # db, hasura, gotify, dashboard
make run CMD=pipeline         # ingest → normalize → geocode → upsert
```

## Dev tools (optional)

```bash
docker compose --profile dev-tools up -d \
  jupyter adminer metabase grafana prometheus
```

| Service | URL |
|---------|-----|
| Public dashboard | http://127.0.0.1:8000 |
| Admin console | http://127.0.0.1:8000/admin |
| Hasura console | http://127.0.0.1:8080/console |
| Gotify | http://127.0.0.1:8081 |
| Adminer | http://127.0.0.1:8082 |
| Metabase | http://127.0.0.1:3000 |
| Grafana | http://127.0.0.1:3001 |
| Prometheus | http://127.0.0.1:9090 |
| JupyterLab | http://127.0.0.1:8888 |

Jupyter token: `JUPYTER_TOKEN` in `.env` (default `change-me`).

## Makefile targets

| Command | Purpose |
|---------|---------|
| `make up` | Start core stack |
| `make down` | Stop all services (including dev-tools) |
| `make run CMD=pipeline` | Run one CLI command in `app` container |
| `make test` | pytest (47+ tests) |
| `make lint` | ruff |
| `make jupyter` | Start Jupyter dev-tools service |
| `make reset-db` | Wipe Postgres volume and recreate |
| `make docker-check CMD=health` | Ephemeral stack test |

## CLI scripts

```bash
python -m notification_rake pipeline
python -m notification_rake health
python -m notification_rake help
```

Available commands: `health`, `ingest`, `normalize`, `upsert`, `pipeline`, `seed`, `hasura_track`, `add_model`.

## Notebooks

| Notebook | Topic |
|----------|--------|
| `01_craigslist_ingestion.ipynb` | RSS fetch + geocode |
| `02_normalize_listings.ipynb` | Catalog matching |
| `03_geospatial_search.ipynb` | Radius search |
| `04_yahoo_phase0.ipynb` | Yahoo API + proxy recon |

See [Development](Development).

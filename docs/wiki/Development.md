# Development

## Local Python env

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
make test
make lint
```

## Tests

```bash
make test    # pytest, 47+ tests
make lint    # ruff
make check   # lint + test + docker-build
```

Key test modules:

| File | Covers |
|------|--------|
| `test_web.py` | Flask dashboard + admin auth |
| `test_search.py` | Search SQL builder |
| `test_pipeline.py` | Pipeline orchestration |
| `test_yahoo_client.py` | Yahoo fixture parse |
| `test_admin_console.py` | Ops actions |

## Project layout

See [Architecture](Architecture).

## Notebooks

Start Jupyter:

```bash
make jupyter
# http://127.0.0.1:8888 — token from JUPYTER_TOKEN
```

| Notebook | Purpose |
|----------|---------|
| `01_craigslist_ingestion.ipynb` | RSS + geocode |
| `02_normalize_listings.ipynb` | Catalog matching |
| `03_geospatial_search.ipynb` | `search_within_radius` |
| `04_yahoo_phase0.ipynb` | Yahoo API + proxy checklist |

Package imports use layered paths, e.g.:

```python
from notification_rake.ingestion import fetch_listings
from notification_rake.workflow import run_pipeline
from notification_rake.search import search_listings, ListingSearch
```

## Web development

Dashboard is Flask served by gunicorn in Docker:

```bash
docker compose build dashboard
docker compose up -d dashboard
```

Static files: `src/notification_rake/web/static/`

Templates: `src/notification_rake/web/templates/`

## Agent skills

Optional Cursor skills in `.agent/` — `make install-skills`.

## Code reference

Detailed module list: repo `docs/functions.md`.

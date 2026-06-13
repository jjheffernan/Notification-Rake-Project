"""Application settings — single source for env-backed configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_repo_root() -> Path:
    """Locate project root (works for src/ layout and installed copies in a checkout)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "scripts").is_dir():
            return parent
    return _REPO_ROOT


_PROJECT_ROOT = _find_repo_root()

# Defaults mirrored in pyproject.toml [tool.notification-rake] and .env.example
DEFAULT_POSTGRES_USER = "rake"
DEFAULT_POSTGRES_PASSWORD = "change-me"
DEFAULT_POSTGRES_DB = "rake"
DEFAULT_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
DEFAULT_CRAIGSLIST_RSS = (
    "https://sfbay.craigslist.org/search/cta?format=rss&query=toyota+camry"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = DEFAULT_POSTGRES_USER
    postgres_password: str = DEFAULT_POSTGRES_PASSWORD
    postgres_db: str = DEFAULT_POSTGRES_DB
    database_url: str = ""

    craigslist_search_rss: str = DEFAULT_CRAIGSLIST_RSS

    yahoo_app_id: str = ""
    yahoo_auction_api_base: str = "https://auctions.yahooapis.jp/AuctionWebService/V2"
    yahoo_vehicle_auccat: int = 26360
    yahoo_ingest_page_size: int = 50
    yahoo_requests_per_day: int = 45_000
    default_dest_country: str = "US"
    fx_usd_jpy: float = 150.0
    fx_usd_gbp: float = 0.79
    fx_usd_eur: float = 0.92

    gotify_url: str = "http://gotify:80"
    gotify_token: str = ""
    gotify_public_url: str = "http://127.0.0.1:8081"
    hasura_url: str = "http://hasura:8080"
    hasura_admin_secret: str = "change-me"
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    geocode_user_agent: str = "notification-rake/0.1.0"
    default_lon: float = -122.4194
    default_lat: float = 37.7749
    log_level: str = "INFO"

    dashboard_secret_key: str = "change-me-dashboard-secret"
    dashboard_port: int = 8000
    admin_user: str = "admin"
    admin_password: str = "change-me"

    adminer_url: str = "http://127.0.0.1:8082"
    metabase_url: str = "http://127.0.0.1:3000"
    metabase_internal_url: str = "http://metabase:3000"
    grafana_url: str = "http://127.0.0.1:3001"
    prometheus_internal_url: str = "http://prometheus:9090"
    jupyter_url: str = "http://127.0.0.1:8888"
    jupyter_internal_url: str = "http://jupyter:8888"

    meilisearch_url: str = "http://meilisearch:7700"
    meilisearch_api_key: str = ""
    meilisearch_public_url: str = "http://127.0.0.1:7700"
    search_engine: str = "auto"  # postgres | meilisearch | auto

    copart_enabled: bool = True
    copart_api_base: str = ""
    copart_api_key: str = ""
    copart_api_mode: str = "auto"  # auto | fixture | provider | web
    copart_requests_per_day: int = 5000
    copart_ingest_limit: int = 50

    eu_marketplaces_enabled: bool = True
    eu_ingest_limit: int = 50

    carsandbids_enabled: bool = True
    carsandbids_api_base: str = ""
    carsandbids_api_key: str = ""
    carsandbids_api_mode: str = "auto"  # auto | fixture | provider
    carsandbids_requests_per_day: int = 2000
    carsandbids_ingest_limit: int = 50

    scheduled_search_refresh_all: bool = True
    scheduled_search_default_interval_min: int = 360

    fred_api_key: str = ""
    cis_automotive_api_base: str = "https://api.autodealerdata.com"
    cis_automotive_jwt: str = ""
    cis_automotive_api_key: str = ""
    cis_automotive_api_secret: str = ""
    cis_automotive_region: str = "REGION_STATE_CA"
    cis_automotive_sales_month: str = ""

    image_proxy_enabled: bool = True
    image_proxy_allowed_hosts: str = (
        "cs.copart.com,img.copart.com,i.ebayimg.com,example.yahoo,auctions.c.yimg.jp,"
        "craigslist.org,images.craigslist.org,img.gumtree.com,prod.pictures.autoscout24.net,"
        "img.classic.mobile.de,media.carsandbids.com"
    )

    rake_scripts_dir: Path = Field(
        default=DEFAULT_SCRIPTS_DIR,
        validation_alias="RAKE_SCRIPTS_DIR",
    )

    @model_validator(mode="after")
    def _fill_database_url(self) -> Settings:
        if not self.database_url:
            self.database_url = (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@db:5432/{self.postgres_db}"
            )
        return self

    @property
    def scripts_dir(self) -> Path:
        return self.rake_scripts_dir

    @property
    def image_proxy_hosts(self) -> list[str]:
        return [
            h.strip().lower()
            for h in str(self.image_proxy_allowed_hosts).split(",")
            if h.strip()
        ]


settings = Settings()

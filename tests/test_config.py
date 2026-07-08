import logging

import pytest

from notification_rake.config import Settings, configure_logging

_PRODUCTION_SECRETS = {
    "postgres_password": "prod-pg-secret",
    "hasura_admin_secret": "prod-hasura-secret",
    "dashboard_secret_key": "prod-dashboard-secret",
    "admin_password": "prod-admin-secret",
    "gotify_token": "prod-gotify-token",
    "meilisearch_api_key": "prod-meili-key",
    "credential_encryption_key": "prod-credential-key",
    "database_url": "postgresql://rake:prod-pg-secret@db:5432/rake",
}


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("GOTIFY_TOKEN", "secret")
    monkeypatch.setenv("GOTIFY_URL", "http://localhost:8081")
    s = Settings()
    assert s.gotify_token == "secret"
    assert s.gotify_url == "http://localhost:8081"


def test_database_url_from_postgres_env():
    s = Settings(
        _env_file=None,
        database_url="",
        postgres_user="u",
        postgres_password="p",
        postgres_db="d",
    )
    assert s.database_url == "postgresql://u:p@db:5432/d"


def test_scripts_dir_from_env(monkeypatch, tmp_path):
    scripts = tmp_path / "custom-scripts"
    scripts.mkdir()
    monkeypatch.setenv("RAKE_SCRIPTS_DIR", str(scripts))
    s = Settings(_env_file=None)
    assert s.scripts_dir == scripts


def test_settings_ignore_unknown_env(monkeypatch):
    monkeypatch.setenv("NOT_A_SETTING", "nope")
    s = Settings()
    assert not hasattr(s, "not_a_setting")


def test_production_rejects_placeholder_secrets():
    with pytest.raises(ValueError, match="RAKE_ENV=production"):
        Settings(_env_file=None, rake_env="production")


def test_production_accepts_real_secrets():
    s = Settings(_env_file=None, rake_env="production", **_PRODUCTION_SECRETS)
    assert s.rake_env == "production"
    assert s.postgres_password == "prod-pg-secret"


def test_log_level_from_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")
    s = Settings(_env_file=None)
    assert s.log_level == "debug"


@pytest.mark.parametrize(
    "level,expected",
    [
        ("DEBUG", logging.DEBUG),
        ("info", logging.INFO),
        ("Warning", logging.WARNING),
        ("ERROR", logging.ERROR),
    ],
)
def test_configure_logging_sets_levels(level, expected):
    configure_logging(level)
    assert logging.getLogger().level == expected
    assert logging.getLogger("notification_rake").level == expected


def test_configure_logging_rejects_invalid_level():
    with pytest.raises(ValueError, match="Invalid log level"):
        configure_logging("TRACE")

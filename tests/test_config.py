from notification_rake.config import Settings


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

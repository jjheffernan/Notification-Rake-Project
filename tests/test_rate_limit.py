from unittest.mock import patch

import pytest

from notification_rake.web import create_app
from notification_rake.web.rate_limit import reset_rate_limits


def _csrf_from_login_page(client):
    import re

    resp = client.get("/admin/login")
    match = re.search(rb'name="csrf_token" value="([^"]+)"', resp.data)
    assert match is not None
    return match.group(1).decode()


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("notification_rake.config.settings.api_rate_limit", 3)
    monkeypatch.setattr("notification_rake.config.settings.api_rate_limit_window_sec", 60)
    monkeypatch.setattr("notification_rake.config.settings.admin_login_rate_limit", 2)
    monkeypatch.setattr(
        "notification_rake.config.settings.admin_login_rate_limit_window_sec", 60
    )
    app = create_app()
    return app.test_client()


def test_api_rate_limit_returns_429(client):
    env = {"REMOTE_ADDR": "203.0.113.10"}
    with patch(
        "notification_rake.web.blueprints.public.search_listings",
        return_value=([], 0),
    ):
        for _ in range(3):
            resp = client.get("/api/listings", environ_base=env)
            assert resp.status_code == 200
        resp = client.get("/api/listings", environ_base=env)
    assert resp.status_code == 429
    assert resp.get_json()["error"] == "Too many requests"


def test_api_rate_limit_is_per_ip(client):
    with patch(
        "notification_rake.web.blueprints.public.search_listings",
        return_value=([], 0),
    ):
        for _ in range(3):
            client.get("/api/listings", environ_base={"REMOTE_ADDR": "203.0.113.1"})
        blocked = client.get("/api/listings", environ_base={"REMOTE_ADDR": "203.0.113.1"})
        allowed = client.get("/api/listings", environ_base={"REMOTE_ADDR": "203.0.113.2"})
    assert blocked.status_code == 429
    assert allowed.status_code == 200


def test_health_not_rate_limited(client, monkeypatch):
    monkeypatch.setattr("notification_rake.config.settings.meilisearch_url", "")
    with patch(
        "notification_rake.web.blueprints.public.check_connection",
        return_value=True,
    ):
        for _ in range(5):
            resp = client.get("/health", environ_base={"REMOTE_ADDR": "203.0.113.99"})
    assert resp.status_code == 200


def test_admin_login_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr("notification_rake.web.auth.settings.admin_user", "admin")
    monkeypatch.setattr("notification_rake.web.auth.settings.admin_password", "secret")
    env = {"REMOTE_ADDR": "198.51.100.7"}
    csrf = _csrf_from_login_page(client)
    for _ in range(2):
        resp = client.post(
            "/admin/login",
            data={"csrf_token": csrf, "username": "admin", "password": "wrong"},
            environ_base=env,
        )
        assert resp.status_code == 401
        csrf = _csrf_from_login_page(client)
    resp = client.post(
        "/admin/login",
        data={"csrf_token": csrf, "username": "admin", "password": "wrong"},
        environ_base=env,
    )
    assert resp.status_code == 429


def test_admin_login_get_not_rate_limited(client):
    for _ in range(5):
        resp = client.get("/admin/login", environ_base={"REMOTE_ADDR": "198.51.100.8"})
    assert resp.status_code == 200

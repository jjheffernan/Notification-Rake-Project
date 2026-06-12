from unittest.mock import patch

from notification_rake.admin import LayerStats
from notification_rake.web import create_app


def test_public_listings_api():
    app = create_app()
    client = app.test_client()
    with patch(
        "notification_rake.web.blueprints.public.search_listings",
        return_value=([{"id": "1", "title": "Camry"}], 1),
    ):
        resp = client.get("/api/listings")
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "public, max-age=60"
    data = resp.get_json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Camry"


def test_market_index_page():
    app = create_app()
    client = app.test_client()
    resp = client.get("/m")
    assert resp.status_code == 200
    assert b"Market data" in resp.data


def test_accounts_page():
    app = create_app()
    client = app.test_client()
    resp = client.get("/accounts")
    assert resp.status_code == 200
    assert b"Connected accounts" in resp.data
    assert b"carsandbids" in resp.data


def test_api_routes():
    app = create_app()
    client = app.test_client()
    sample = [{"slug": "jp", "label": "Japan", "listings": 5, "sources": ["yahoo_auctions_jp"]}]
    with patch(
        "notification_rake.web.blueprints.public.list_ingest_routes",
        return_value=sample,
    ):
        resp = client.get("/api/routes")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["routes"][0]["slug"] == "jp"


def test_market_models_api():
    app = create_app()
    client = app.test_client()
    sample = [{"make": "Nissan", "model": "Stagea", "listings": 2, "url": "/m/nissan/stagea"}]
    with patch(
        "notification_rake.web.blueprints.public.list_model_markets",
        return_value=sample,
    ):
        resp = client.get("/api/market/models")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["models"][0]["model"] == "Stagea"


def test_dashboard_includes_design_system():
    app = create_app()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"rake.css" in resp.data
    assert b"rake.js" in resp.data


def test_admin_requires_login():
    app = create_app()
    client = app.test_client()
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["Location"].endswith("/admin/login")


def test_admin_login_and_console(monkeypatch):
    monkeypatch.setattr("notification_rake.web.auth.settings.admin_user", "admin")
    monkeypatch.setattr("notification_rake.web.auth.settings.admin_password", "secret")

    overview = {
        "services": [],
        "layers": LayerStats(0, 0, 0, 0, 0).__dict__,
        "sources": [],
        "syncs": [],
        "jobs": [],
        "actions": ["pipeline"],
    }

    app = create_app()
    client = app.test_client()
    login = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret"},
        follow_redirects=False,
    )
    assert login.status_code == 303

    with patch("notification_rake.web.blueprints.admin.admin_overview", return_value=overview):
        admin = client.get("/admin")
    assert admin.status_code == 200
    assert b"Stack health" in admin.data
    assert b"Runtime actions" in admin.data


def test_admin_api_requires_session():
    app = create_app()
    client = app.test_client()
    resp = client.get("/admin/api/overview")
    assert resp.status_code == 401


def test_admin_api_overview_when_logged_in(monkeypatch):
    monkeypatch.setattr("notification_rake.web.auth.settings.admin_user", "admin")
    monkeypatch.setattr("notification_rake.web.auth.settings.admin_password", "secret")

    app = create_app()
    client = app.test_client()
    client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret"},
        follow_redirects=False,
    )

    empty_overview = {
        "services": [],
        "layers": {},
        "sources": [],
        "syncs": [],
        "jobs": [],
        "actions": [],
    }
    with patch(
        "notification_rake.web.blueprints.admin.admin_overview",
        return_value=empty_overview,
    ):
        resp = client.get("/admin/api/overview")
    assert resp.status_code == 200

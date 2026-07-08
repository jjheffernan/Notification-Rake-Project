"""Integration tests for core buyer UX flows (sign-in, search, watchlist, accounts)."""

from __future__ import annotations

import re
import uuid
from unittest.mock import patch

import pytest

from notification_rake.search import ListingSearch
from notification_rake.storage.accounts import ConnectedAccount
from notification_rake.storage.scheduled_searches import ScheduledSearch
from notification_rake.web import create_app

OTHER_PROFILE = "22222222-2222-4222-8222-222222222222"
SAMPLE_LISTING = {
    "id": "listing-1",
    "title": "2018 Toyota Camry SE",
    "make": "Toyota",
    "model": "Camry",
    "price": 18500,
    "source": "craigslist",
}


@pytest.fixture
def client():
    return create_app().test_client()


def _create_profile(client) -> str:
    resp = client.post("/api/profile")
    assert resp.status_code == 200
    profile_id = resp.get_json()["profile_id"]
    uuid.UUID(profile_id)
    return profile_id


WATCHLIST_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ACCOUNT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _sample_watchlist(
    profile_id: str, *, search_id: str = WATCHLIST_ID
) -> ScheduledSearch:
    return ScheduledSearch(
        id=search_id,
        profile_id=profile_id,
        name="Camry alerts",
        query_json={"q": "camry", "make": "Toyota"},
        alert_enabled=True,
        enabled=True,
        interval_minutes=360,
        ingest_routes=["us-retail"],
        last_run_at=None,
        next_run_at=None,
        last_match_count=0,
        last_new_count=0,
        last_seen_ids=[],
        created_at="2026-01-01T00:00:00+00:00",
    )


def _sample_account(
    profile_id: str, *, account_id: str = ACCOUNT_ID
) -> ConnectedAccount:
    return ConnectedAccount(
        id=account_id,
        profile_id=profile_id,
        provider="ebay",
        label="My eBay",
        config={"api_key": "sekret-key", "query": "camry"},
        enabled=True,
        last_sync_at=None,
        last_status=None,
        listings_synced=0,
    )


def test_signin_page_supports_profile_create_and_restore(client):
    resp = client.get("/signin")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Sign in" in html
    assert "signin-create-btn" in html
    assert "signin-restore-form" in html
    assert "profile-id-input" in html
    assert "rake.js" in html
    assert "signin.js" in html


def test_create_profile_returns_valid_uuid(client):
    profile_id = _create_profile(client)
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        profile_id,
        flags=re.I,
    )


def test_existing_profile_uuid_accepted_by_private_apis(client):
    profile_id = "11111111-1111-4111-8111-111111111111"
    with patch(
        "notification_rake.web.blueprints.public.list_scheduled_searches",
        return_value=[],
    ) as list_searches:
        resp = client.get(f"/api/scheduled-searches?profile_id={profile_id}")
    assert resp.status_code == 200
    assert list_searches.call_args.kwargs["profile_id"] == profile_id


def test_private_apis_reject_invalid_profile_uuid(client):
    for path in (
        "/api/scheduled-searches?profile_id=not-a-uuid",
        "/api/accounts?profile_id=bad",
    ):
        resp = client.get(path)
        assert resp.status_code == 400
        assert b"invalid profile_id" in resp.data


def test_vehicle_search_returns_listings(client):
    with patch(
        "notification_rake.web.blueprints.public.search_listings",
        return_value=([SAMPLE_LISTING], 1),
    ):
        resp = client.get("/api/listings?q=camry&make=Toyota&limit=12")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["limit"] == 12
    assert data["items"][0]["title"] == SAMPLE_LISTING["title"]


def test_vehicle_search_forwards_filters_to_backend(client):
    with patch(
        "notification_rake.web.blueprints.public.search_listings",
        return_value=([], 0),
    ) as search_listings:
        client.get(
            "/api/listings"
            "?q=stagea&make=Nissan&model=Stagea&source=yahoo_auctions_jp"
            "&price_max=25000&sort=price_asc&limit=10&offset=5"
        )
    search = search_listings.call_args[0][1]
    assert isinstance(search, ListingSearch)
    assert search.q == "stagea"
    assert search.make == "Nissan"
    assert search.model == "Stagea"
    assert search.source == "yahoo_auctions_jp"
    assert search.price_max == 25000
    assert search.sort == "price_asc"
    assert search.limit == 10
    assert search.offset == 5


def test_market_index_page_reachable(client):
    resp = client.get("/m")
    assert resp.status_code == 200
    assert b"Market data" in resp.data


def test_watchlist_add_list_remove_flow(client):
    profile_id = _create_profile(client)
    search = _sample_watchlist(profile_id)

    with patch(
        "notification_rake.web.blueprints.public.upsert_scheduled_search",
        return_value=search,
    ) as upsert:
        create = client.post(
            "/api/scheduled-searches",
            json={
                "profile_id": profile_id,
                "name": search.name,
                "query_json": search.query_json,
                "ingest_routes": search.ingest_routes,
            },
        )
    assert create.status_code == 200
    assert upsert.call_args.kwargs["profile_id"] == profile_id
    created = create.get_json()
    assert created["name"] == search.name
    assert created["query_json"] == search.query_json

    with patch(
        "notification_rake.web.blueprints.public.list_scheduled_searches",
        return_value=[search],
    ) as list_searches:
        listed = client.get(f"/api/scheduled-searches?profile_id={profile_id}")
    assert listed.status_code == 200
    assert list_searches.call_args.kwargs["profile_id"] == profile_id
    assert listed.get_json()["searches"][0]["id"] == search.id

    with patch(
        "notification_rake.web.blueprints.public.delete_scheduled_search",
        return_value=True,
    ) as delete_search:
        removed = client.delete(
            f"/api/scheduled-searches/{search.id}?profile_id={profile_id}"
        )
    assert removed.status_code == 200
    assert delete_search.call_args[0][2] == profile_id
    assert removed.get_json()["ok"] is True


def test_watchlist_other_profile_cannot_delete(client):
    _create_profile(client)
    search_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    with patch(
        "notification_rake.web.blueprints.public.delete_scheduled_search",
        return_value=False,
    ) as delete_search:
        resp = client.delete(
            f"/api/scheduled-searches/{search_id}?profile_id={OTHER_PROFILE}"
        )
    assert resp.status_code == 404
    assert delete_search.call_args[0][2] == OTHER_PROFILE


def test_accounts_connect_list_disconnect_flow(client):
    profile_id = _create_profile(client)
    account = _sample_account(profile_id)

    with patch(
        "notification_rake.web.blueprints.public.upsert_account",
        return_value=account,
    ) as upsert:
        connect = client.post(
            "/api/accounts",
            json={
                "profile_id": profile_id,
                "provider": account.provider,
                "label": account.label,
                "config": {"api_key": "sekret-key", "query": "camry"},
            },
        )
    assert connect.status_code == 200
    assert upsert.call_args.kwargs["profile_id"] == profile_id
    connected = connect.get_json()
    assert connected["id"] == account.id
    assert connected["config"]["api_key"] == "***"
    assert "sekret-key" not in connect.get_data(as_text=True)

    with patch(
        "notification_rake.web.blueprints.public.list_accounts",
        return_value=[account],
    ) as list_accounts:
        listed = client.get(f"/api/accounts?profile_id={profile_id}")
    assert listed.status_code == 200
    assert list_accounts.call_args[0][1] == profile_id
    assert listed.get_json()["accounts"][0]["id"] == account.id

    with patch(
        "notification_rake.web.blueprints.public.delete_account",
        return_value=True,
    ) as delete_account:
        removed = client.delete(
            f"/api/accounts/{account.id}?profile_id={profile_id}"
        )
    assert removed.status_code == 200
    assert delete_account.call_args[0][2] == profile_id
    assert removed.get_json()["ok"] is True


def test_accounts_other_profile_sees_empty_list(client):
    _create_profile(client)
    with patch(
        "notification_rake.web.blueprints.public.list_accounts",
        return_value=[],
    ) as list_accounts:
        resp = client.get(f"/api/accounts?profile_id={OTHER_PROFILE}")
    assert resp.status_code == 200
    assert list_accounts.call_args[0][1] == OTHER_PROFILE
    assert resp.get_json()["accounts"] == []


def test_buyer_journey_signin_search_watchlist_accounts(client):
    profile_id = _create_profile(client)

    with patch(
        "notification_rake.web.blueprints.public.search_listings",
        return_value=([SAMPLE_LISTING], 1),
    ):
        search_resp = client.get("/api/listings?q=camry&make=Toyota")
    assert search_resp.status_code == 200
    assert search_resp.get_json()["total"] == 1

    watchlist = _sample_watchlist(profile_id)
    with patch(
        "notification_rake.web.blueprints.public.upsert_scheduled_search",
        return_value=watchlist,
    ):
        watch_resp = client.post(
            "/api/scheduled-searches",
            json={
                "profile_id": profile_id,
                "name": watchlist.name,
                "query_json": watchlist.query_json,
            },
        )
    assert watch_resp.status_code == 200

    account = _sample_account(profile_id)
    with patch(
        "notification_rake.web.blueprints.public.upsert_account",
        return_value=account,
    ):
        account_resp = client.post(
            "/api/accounts",
            json={
                "profile_id": profile_id,
                "provider": "ebay",
                "label": "Journey eBay",
                "config": {"api_key": "key", "query": "camry"},
            },
        )
    assert account_resp.status_code == 200

    with patch(
        "notification_rake.web.blueprints.public.list_scheduled_searches",
        return_value=[watchlist],
    ):
        listed_watch = client.get(f"/api/scheduled-searches?profile_id={profile_id}")
    with patch(
        "notification_rake.web.blueprints.public.list_accounts",
        return_value=[account],
    ):
        listed_accounts = client.get(f"/api/accounts?profile_id={profile_id}")

    assert listed_watch.get_json()["searches"][0]["name"] == watchlist.name
    assert listed_accounts.get_json()["accounts"][0]["provider"] == "ebay"

    with patch(
        "notification_rake.web.blueprints.public.delete_scheduled_search",
        return_value=True,
    ):
        assert client.delete(
            f"/api/scheduled-searches/{watchlist.id}?profile_id={profile_id}"
        ).status_code == 200
    with patch(
        "notification_rake.web.blueprints.public.delete_account",
        return_value=True,
    ):
        assert client.delete(
            f"/api/accounts/{account.id}?profile_id={profile_id}"
        ).status_code == 200


def test_buyer_pages_load_without_operator_nav(client):
    for path in ("/", "/signin", "/watchlist", "/accounts", "/m"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert b"Operator" not in resp.data
        assert b"/admin/login" not in resp.data

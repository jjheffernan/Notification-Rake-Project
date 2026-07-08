"""Profile isolation tests for connected accounts APIs."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from notification_rake.storage.accounts import ConnectedAccount
from notification_rake.web import create_app

PROFILE_A = "11111111-1111-4111-8111-111111111111"
PROFILE_B = "22222222-2222-4222-8222-222222222222"
ACCOUNT_A = ConnectedAccount(
    id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    profile_id=PROFILE_A,
    provider="carsandbids",
    label="My C&B",
    config={"token": "secret"},
    enabled=True,
    last_sync_at=None,
    last_status=None,
    listings_synced=0,
)


@pytest.fixture
def client():
    return create_app().test_client()


def test_list_accounts_requires_profile_id(client):
    resp = client.get("/api/accounts")
    assert resp.status_code == 400
    assert b"profile_id required" in resp.data


def test_list_accounts_rejects_invalid_profile_id(client):
    resp = client.get("/api/accounts?profile_id=not-a-uuid")
    assert resp.status_code == 400
    assert b"invalid profile_id" in resp.data


def test_list_accounts_scoped_to_requested_profile(client):
    with patch(
        "notification_rake.web.blueprints.public.list_accounts",
        return_value=[ACCOUNT_A],
    ) as list_accounts:
        resp = client.get(f"/api/accounts?profile_id={PROFILE_A}")
    assert resp.status_code == 200
    assert list_accounts.call_args[0][1] == PROFILE_A
    data = resp.get_json()
    assert len(data["accounts"]) == 1
    assert data["accounts"][0]["id"] == ACCOUNT_A.id
    assert "config" not in data["accounts"][0]


def test_list_accounts_other_profile_sees_empty_list(client):
    with patch(
        "notification_rake.web.blueprints.public.list_accounts",
        return_value=[],
    ) as list_accounts:
        resp = client.get(f"/api/accounts?profile_id={PROFILE_B}")
    assert resp.status_code == 200
    assert list_accounts.call_args[0][1] == PROFILE_B
    assert resp.get_json()["accounts"] == []


def test_disconnect_account_requires_profile_id(client):
    resp = client.delete(f"/api/accounts/{ACCOUNT_A.id}")
    assert resp.status_code == 400
    assert b"profile_id required" in resp.data


def test_disconnect_account_wrong_profile_returns_404(client):
    with patch(
        "notification_rake.web.blueprints.public.delete_account",
        return_value=False,
    ) as delete_account:
        resp = client.delete(f"/api/accounts/{ACCOUNT_A.id}?profile_id={PROFILE_B}")
    assert resp.status_code == 404
    assert delete_account.call_args[0][1] == ACCOUNT_A.id
    assert delete_account.call_args[0][2] == PROFILE_B

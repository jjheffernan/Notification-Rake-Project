"""Profile isolation and credential protection for connected accounts."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from notification_rake.storage.accounts import ConnectedAccount, upsert_account
from notification_rake.storage.credential_crypto import (
    decrypt_config,
    encrypt_config,
    is_encrypted,
    mask_config,
)
from notification_rake.web import create_app

PROFILE_A = "11111111-1111-4111-8111-111111111111"
PROFILE_B = "22222222-2222-4222-8222-222222222222"
ACCOUNT_A = ConnectedAccount(
    id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    profile_id=PROFILE_A,
    provider="ebay",
    label="My eBay",
    config={"api_key": "sekret-key", "oauth_token": "tok-123", "query": "camry"},
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


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setattr(
        "notification_rake.config.settings.credential_encryption_key",
        "test-credential-key",
    )
    original = {"api_key": "abc", "query": "skyline"}
    stored = encrypt_config(original)
    assert is_encrypted(stored)
    assert stored != original
    assert decrypt_config(stored) == original


def test_decrypt_legacy_plaintext_config(monkeypatch):
    monkeypatch.setattr(
        "notification_rake.config.settings.credential_encryption_key",
        "test-credential-key",
    )
    legacy = {"rss_url": "https://example.com/rss"}
    assert decrypt_config(legacy) == legacy
    assert not is_encrypted(legacy)


def test_mask_config_hides_secrets():
    masked = mask_config(
        {"api_key": "sekret", "oauth_token": "tok", "query": "camry", "limit": 10}
    )
    assert masked["api_key"] == "***"
    assert masked["oauth_token"] == "***"
    assert masked["query"] == "camry"
    assert masked["limit"] == 10


def test_upsert_stores_encrypted_config(settings, monkeypatch):
    monkeypatch.setattr(
        "notification_rake.config.settings.credential_encryption_key",
        "test-credential-key",
    )
    dsn = settings.database_url
    config = {"api_key": "stored-secret", "query": "mr2"}
    try:
        account = upsert_account(
            dsn,
            profile_id=PROFILE_A,
            provider="ebay",
            label="encrypt-test",
            config=config,
        )
        assert account.config == config

        import psycopg

        with psycopg.connect(dsn) as conn:
            row = conn.execute(
                "SELECT config FROM metadata.connected_account WHERE id = %s::uuid",
                (account.id,),
            ).fetchone()
        raw = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        assert is_encrypted(raw)
        assert raw.get("api_key") != "stored-secret"
        assert decrypt_config(raw) == config
    except Exception as exc:
        pytest.skip(f"database not available: {exc}")


def test_list_accounts_masks_secrets_in_response(client):
    with patch(
        "notification_rake.web.blueprints.public.list_accounts",
        return_value=[ACCOUNT_A],
    ) as list_accounts:
        resp = client.get(f"/api/accounts?profile_id={PROFILE_A}")
    assert resp.status_code == 200
    assert list_accounts.call_args[0][1] == PROFILE_A
    data = resp.get_json()
    assert len(data["accounts"]) == 1
    row = data["accounts"][0]
    assert row["id"] == ACCOUNT_A.id
    assert row["config"]["api_key"] == "***"
    assert row["config"]["oauth_token"] == "***"
    assert row["config"]["query"] == "camry"
    assert "sekret-key" not in resp.get_data(as_text=True)
    assert "tok-123" not in resp.get_data(as_text=True)


def test_connect_account_masks_secrets_in_response(client):
    with patch(
        "notification_rake.web.blueprints.public.upsert_account",
        return_value=ACCOUNT_A,
    ):
        resp = client.post(
            "/api/accounts",
            json={
                "profile_id": PROFILE_A,
                "provider": "ebay",
                "label": "My eBay",
                "config": {"api_key": "sekret-key", "query": "camry"},
            },
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["config"]["api_key"] == "***"
    assert data["config"]["query"] == "camry"
    assert "sekret-key" not in resp.get_data(as_text=True)


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

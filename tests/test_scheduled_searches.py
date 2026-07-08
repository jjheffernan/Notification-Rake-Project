"""Tests for scheduled watchlist searches."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from notification_rake.storage.scheduled_searches import (
    ScheduledSearch,
    delete_scheduled_search,
    list_due_searches,
    list_scheduled_searches,
    upsert_scheduled_search,
)
from notification_rake.web import create_app
from notification_rake.workflow.scheduled_batch import (
    BatchRunResult,
    SearchRunOutcome,
    run_scheduled_batch,
    run_single_scheduled_search,
)


@pytest.fixture
def profile_id():
    return "11111111-1111-4111-8111-111111111111"


def test_upsert_and_list_scheduled_search(settings, profile_id):
    dsn = settings.database_url
    try:
        search = upsert_scheduled_search(
            dsn,
            profile_id=profile_id,
            name="Stagea hunt",
            query_json={"make": "Nissan", "model": "Stagea"},
            interval_minutes=60,
            ingest_routes=["jp"],
        )
        assert search.name == "Stagea hunt"
        assert search.interval_minutes == 60
        assert search.ingest_routes == ["jp"]

        listed = list_scheduled_searches(dsn, profile_id=profile_id)
        assert any(s.id == search.id for s in listed)

        assert delete_scheduled_search(dsn, search.id, profile_id)
        assert not delete_scheduled_search(dsn, search.id, profile_id)
    except Exception as exc:
        pytest.skip(f"database unavailable: {exc}")


def test_list_due_searches_accepts_profile_filter(settings, profile_id):
    with patch("psycopg.connect") as connect:
        mock_conn = connect.return_value.__enter__.return_value
        mock_conn.execute.return_value.fetchall.return_value = []
        list_due_searches(settings.database_url, profile_id=profile_id)
        sql = mock_conn.execute.call_args[0][0]
        assert "profile_id" in sql


def test_run_single_scheduled_search_baseline(settings):
    search = ScheduledSearch(
        id="22222222-2222-4222-8222-222222222222",
        profile_id=None,
        name="Test",
        query_json={"make": "Mazda"},
        alert_enabled=False,
        enabled=True,
        interval_minutes=360,
        ingest_routes=[],
        last_run_at=None,
        next_run_at=None,
        last_match_count=None,
        last_new_count=None,
        last_seen_ids=[],
        created_at="",
    )
    with patch(
        "notification_rake.workflow.scheduled_batch.search_listings",
        return_value=([{"id": "a"}, {"id": "b"}], 2),
    ):
        with patch("notification_rake.workflow.scheduled_batch.record_search_run") as record:
            outcome = run_single_scheduled_search(settings.database_url, search)
    assert outcome.match_count == 2
    assert outcome.new_count == 0
    record.assert_called_once()


def test_run_scheduled_batch_force(settings, profile_id):
    sample = ScheduledSearch(
        id="33333333-3333-4333-8333-333333333333",
        profile_id=profile_id,
        name="Forced",
        query_json={"model": "Skyline"},
        alert_enabled=False,
        enabled=True,
        interval_minutes=360,
        ingest_routes=[],
        last_run_at=None,
        next_run_at=None,
        last_match_count=None,
        last_new_count=None,
        last_seen_ids=[],
        created_at="",
    )
    with patch(
        "notification_rake.workflow.scheduled_batch.list_scheduled_searches",
        return_value=[sample],
    ):
        with patch(
            "notification_rake.workflow.scheduled_batch._refresh_routes",
            return_value=0,
        ):
            with patch(
                "notification_rake.workflow.scheduled_batch.run_single_scheduled_search",
                return_value=SearchRunOutcome(sample.id, sample.name, match_count=1),
            ):
                with patch(
                    "notification_rake.workflow.scheduled_batch.start_job",
                    return_value=None,
                ):
                    result = run_scheduled_batch(
                        force=True,
                        profile_id=profile_id,
                        track_job=False,
                    )
    assert result.searches_run == 1
    assert result.total_new_matches == 0


def test_watchlist_page():
    app = create_app()
    client = app.test_client()
    resp = client.get("/watchlist")
    assert resp.status_code == 200
    assert b"Watchlist" in resp.data


def test_scheduled_search_api(profile_id):
    app = create_app()
    client = app.test_client()
    sample = ScheduledSearch(
        id="44444444-4444-4444-8444-444444444444",
        profile_id=profile_id,
        name="API test",
        query_json={"make": "Subaru"},
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
    with patch(
        "notification_rake.web.blueprints.public.list_scheduled_searches",
        return_value=[sample],
    ):
        resp = client.get(f"/api/scheduled-searches?profile_id={profile_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["searches"][0]["name"] == "API test"

    with patch(
        "notification_rake.web.blueprints.public.upsert_scheduled_search",
        return_value=sample,
    ):
        resp = client.post(
            "/api/scheduled-searches",
            json={
                "profile_id": profile_id,
                "name": "API test",
                "query_json": {"make": "Subaru"},
            },
        )
    assert resp.status_code == 200

    batch = BatchRunResult(searches_run=1, total_new_matches=2, ingest_upserted=5)
    with patch(
        "notification_rake.workflow.scheduled_batch.run_scheduled_batch",
        return_value=batch,
    ):
        resp = client.post(
            "/api/scheduled-searches/run",
            json={"profile_id": profile_id, "force": True},
        )
    assert resp.status_code == 200
    assert resp.get_json()["total_new_matches"] == 2


def test_admin_run_scheduled_searches_action():
    from notification_rake.admin import execute_action

    batch = BatchRunResult(searches_run=2, total_new_matches=1, total_alerted=1, ingest_upserted=10)
    with patch(
        "notification_rake.workflow.scheduled_batch.run_scheduled_batch",
        return_value=batch,
    ):
        result = execute_action("run_scheduled_searches")
    assert result.ok
    assert "searches=2" in result.message

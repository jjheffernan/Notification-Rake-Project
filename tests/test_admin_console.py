from unittest.mock import patch

from notification_rake.admin import (
    LayerStats,
    ServiceStatus,
    admin_overview,
    execute_action,
)


def test_execute_action_unknown():
    result = execute_action("not-valid")
    assert not result.ok
    assert "unknown" in result.message


def test_execute_action_health_ok():
    services = [
        ServiceStatus("postgres", "PostgreSQL", "ok", "db", "ok"),
        ServiceStatus("hasura", "Hasura", "ok", "url", "ok"),
    ]
    with patch("notification_rake.admin.console.check_services", return_value=services):
        result = execute_action("health")
    assert result.ok


def test_execute_action_health_fail():
    services = [ServiceStatus("postgres", "PostgreSQL", "fail", "db", "down")]
    with patch("notification_rake.admin.console.check_services", return_value=services):
        result = execute_action("health")
    assert not result.ok


def test_admin_overview_shape():
    with patch("notification_rake.admin.console.check_services", return_value=[]):
        with patch(
            "notification_rake.admin.console.layer_stats",
            return_value=LayerStats(1, 2, 3, 4, 5),
        ):
            with patch("notification_rake.admin.console.list_sources", return_value=[]):
                with patch("notification_rake.admin.console.list_recent_syncs", return_value=[]):
                    with patch("notification_rake.admin.console.list_job_runs", return_value=[]):
                        overview = admin_overview()
    assert "services" in overview
    assert overview["layers"]["search_listings"] == 1


def test_execute_action_seed():
    with patch("notification_rake.admin.console.seed_catalog", return_value=8):
        result = execute_action("seed")
    assert result.ok
    assert "8" in result.message

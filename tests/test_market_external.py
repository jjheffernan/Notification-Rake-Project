"""Tests for external market volume integrations."""

from unittest.mock import patch

from notification_rake.integrations.market_external import (
    _parse_production_units,
    fetch_external_volume_data,
    fetch_fred_us_vehicle_sales,
    fetch_nhtsa_model_info,
    fetch_wikipedia_production,
)


def test_parse_production_units():
    assert _parse_production_units("Total production of 1,234,567 units") == 1234567
    assert _parse_production_units("Only 500 built before discontinuation") == 500
    assert _parse_production_units("No numbers here") is None


def test_fred_requires_api_key():
    from notification_rake.integrations import market_external as me

    with patch.object(me.settings, "fred_api_key", ""):
        assert fetch_fred_us_vehicle_sales() == []


def test_fred_parses_observations():
    from notification_rake.integrations import market_external as me

    me._CACHE.clear()
    sample = {
        "observations": [
            {"date": "2026-03-01", "value": "16.1"},
            {"date": "2026-02-01", "value": "."},
            {"date": "2026-01-01", "value": "15.5"},
        ]
    }
    with patch.object(me.settings, "fred_api_key", "test-key"):
        with patch.object(me, "_http_get", return_value=sample):
            rows = fetch_fred_us_vehicle_sales(limit=3)
    assert len(rows) == 2
    assert rows[-1]["sales_saar_millions"] == 16.1


def test_wikipedia_production(settings):
    search_resp = ["query", ["Nissan Stagea"], [], []]
    summary_resp = {
        "extract": "The Nissan Stagea had total production of 250,000 units worldwide.",
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Nissan_Stagea"}},
    }
    with patch(
        "notification_rake.integrations.market_external._http_get",
        side_effect=[search_resp, summary_resp],
    ):
        result = fetch_wikipedia_production("Nissan", "Stagea")
    assert result["units_produced"] == 250000
    assert "wikipedia" in result["source"]


def test_nhtsa_model_match(settings):
    payload = {
        "Results": [
            {"Model_Name": "Camry"},
            {"Model_Name": "Camry Hybrid"},
            {"Model_Name": "Corolla"},
        ]
    }
    with patch(
        "notification_rake.integrations.market_external._http_get",
        return_value=payload,
    ):
        result = fetch_nhtsa_model_info("Toyota", "Camry")
    assert result["match_count"] == 2
    assert "Camry" in result["models_matched"][0]


def test_fetch_external_volume_aggregates(settings):
    with patch(
        "notification_rake.integrations.market_external.fetch_fred_us_vehicle_sales",
        return_value=[{"month": "2026-01-01", "sales_saar_millions": 16.0}],
    ):
        with patch(
            "notification_rake.integrations.market_external.fetch_wikipedia_production",
            return_value={"units_produced": 1000, "source": "wikipedia"},
        ):
            with patch(
                "notification_rake.integrations.market_external.fetch_epa_model_years",
                return_value=None,
            ):
                with patch(
                    "notification_rake.integrations.market_external.fetch_nhtsa_model_info",
                    return_value=None,
                ):
                    with patch(
                        "notification_rake.integrations.market_external._cis_jwt",
                        return_value=None,
                    ):
                        data = fetch_external_volume_data("Toyota", "Camry")
    assert "fred" in data["sources_fetched"]
    assert "wikipedia" in data["sources_fetched"]
    assert data["production"]["units_produced"] == 1000

"""Tests for market onboarding tooling."""

from notification_rake.tools.market_setup import (
    MarketSource,
    MarketSpec,
    audit_market,
    normalize_slug,
    plan_market,
    write_artifacts,
)


def test_normalize_slug():
    assert normalize_slug("Facebook Marketplace") == "facebook_marketplace"
    assert normalize_slug("us-retail") == "us_retail"


def test_plan_market_generates_artifacts():
    spec = MarketSpec(
        route_slug="fr",
        route_label="France",
        country_code="FR",
        region_label="France",
        region_center=(2.3522, 48.8566),
        sources=[
            MarketSource("leboncoin", "https://www.leboncoin.fr"),
            MarketSource("autoscout24_fr", "https://www.autoscout24.fr"),
        ],
        description="French classifieds",
        fetch_strategy="stub",
    )
    plan = plan_market(spec)
    assert "leboncoin" in plan.migration_sql
    assert "FR" in plan.migration_sql
    assert '"fr"' in plan.ingest_routes_snippet
    assert "leboncoin" in plan.regions_snippet
    assert len(plan.checklist) >= 5


def test_write_artifacts(tmp_path):
    spec = MarketSpec(
        route_slug="test_market",
        route_label="Test Market",
        country_code="US",
        sources=[MarketSource("test_source", "https://example.com")],
    )
    plan = plan_market(spec)
    out = write_artifacts(plan, tmp_path)
    assert (out / plan.migration_filename).is_file()
    assert (out / "routes" / "test_market.py").is_file()
    assert (out / "README.md").is_file()


def test_audit_market_fr_not_present():
    spec = MarketSpec(
        route_slug="zz_nonexistent",
        route_label="Nowhere",
        country_code="ZZ",
        sources=[MarketSource("zz_source")],
    )
    results = audit_market(spec)
    assert any(r.name.startswith("INGEST_ROUTES") and not r.ok for r in results)

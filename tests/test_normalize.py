from notification_rake.models import VehicleListing
from notification_rake.transform.normalize import (
    FALLBACK_CATALOG,
    find_model_ref,
    normalize_listing,
    normalize_listings,
)


def test_find_model_ref_camry():
    ref = find_model_ref("2019 Toyota Camry LE - $12,500", list(FALLBACK_CATALOG))
    assert ref is not None
    assert ref.make == "Toyota"
    assert ref.model == "Camry"


def test_find_model_ref_civic():
    ref = find_model_ref("2020 Honda Civic Sport", list(FALLBACK_CATALOG))
    assert ref is not None
    assert ref.model == "Civic"


def test_find_model_ref_no_match():
    assert find_model_ref("mystery wagon", list(FALLBACK_CATALOG)) is None


def test_normalize_listing_sets_fields():
    raw = VehicleListing(source="craigslist", source_listing_id="1", title="2019 Toyota Camry SE")
    out = normalize_listing(raw, list(FALLBACK_CATALOG))
    assert out.make == "Toyota"
    assert out.model == "Camry"


def test_normalize_listings_batch():
    items = [
        VehicleListing(source="c", source_listing_id="1", title="Honda Civic 2020"),
        VehicleListing(source="c", source_listing_id="2", title="random bike"),
    ]
    out = normalize_listings(items, list(FALLBACK_CATALOG))
    assert out[0].model == "Civic"
    assert out[1].make is None

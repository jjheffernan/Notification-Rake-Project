from notification_rake.models import VehicleListing


def test_listing_requires_source_ids():
    listing = VehicleListing(source="craigslist", source_listing_id="abc123")
    assert listing.source == "craigslist"
    assert listing.image_urls == []
    assert listing.scraped_at.tzinfo is not None

from notification_rake.analysis.auction import analyze_copart_lot, damage_severity, normalize_damage
from notification_rake.ingestion.copart.search import CopartLot, search_lots


def test_search_lots_fixture():
    result = search_lots(limit=10)
    assert result.total >= 1
    assert all(isinstance(lot, CopartLot) for lot in result.items)
    assert result.items[0].lot_number


def test_copart_lot_to_listing():
    from notification_rake.ingestion.copart.normalize import copart_lot_to_listing

    lot = search_lots(limit=1).items[0]
    listing = copart_lot_to_listing(lot)
    assert listing.source == "copart"
    assert listing.source_listing_id == lot.lot_number
    assert listing.image_urls
    assert listing.metadata.get("platform") == "copart"
    assert listing.metadata.get("analysis")


def test_damage_analysis():
    lot = CopartLot(
        lot_number="1",
        title="test",
        make="Ford",
        model="F-150",
        year=2015,
        current_bid=1000,
        buy_now_price=None,
        auction_status="upcoming",
        auction_date=None,
        primary_damage="FRONT END",
        secondary_damage=None,
        loss_type="COLLISION",
        run_and_drive=True,
        has_keys=True,
        title_type="SALVAGE",
        odometer=1000,
        yard_name="Y",
        yard_state="CA",
        country="US",
        latitude=1.0,
        longitude=2.0,
        bid_count=1,
        thumbnail_url="https://cs.copart.com/x.jpg",
        gallery_urls=["https://cs.copart.com/x.jpg"],
        copart_url="https://www.copart.com/lot/1",
        raw={},
    )
    analysis = analyze_copart_lot(lot)
    assert analysis["damage_severity"] >= 4
    assert "Runs & drives" in analysis["badges"]
    assert normalize_damage("front end") == "FRONT END"
    assert damage_severity("FRONT END") == 4

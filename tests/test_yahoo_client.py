from notification_rake.ingestion.yahoo import (
    parse_search_items,
    search_vehicle_auctions,
)
from notification_rake.ingestion.yahoo.client import YahooClient, load_sample_search


def test_load_sample_search_has_items():
    payload = load_sample_search()
    items = parse_search_items(payload)
    assert len(items) == 3
    assert items[0].auction_id == "v1200000001"
    assert "スカイライン" in items[0].title


def test_search_without_appid_uses_fixture():
    client = YahooClient(app_id="", api_base="https://example.test/V2")
    result = search_vehicle_auctions(query="スカイライン", client=client)
    assert result.total_available == 142
    assert len(result.items) == 3
    assert result.items[0].current_price_jpy == 850000.0
    assert "buyee" in result.items[0].proxy_links


def test_field_map_includes_proxy_links():
    payload = load_sample_search()
    hit = parse_search_items(payload)[1]
    assert hit.proxy_links["neokyo"].endswith("v1200000002")
    assert hit.source_url.startswith("https://page.auctions.yahoo.co.jp/")

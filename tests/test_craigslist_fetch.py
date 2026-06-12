from notification_rake.ingestion.craigslist import fetch_listings, load_sample_rss, parse_rss_items


def test_load_sample_rss_parses():
    listings = list(parse_rss_items(load_sample_rss()))
    assert len(listings) == 2
    assert listings[0].source_listing_id == "sample12345"
    assert listings[0].price == 12500.0


def test_fetch_listings_falls_back_on_403(monkeypatch):
    import httpx

    def fake_fetch(_url, *, user_agent=...):
        req = httpx.Request("GET", "https://example.com/rss")
        resp = httpx.Response(403, request=req)
        raise httpx.HTTPStatusError("403", request=req, response=resp)

    monkeypatch.setattr("notification_rake.ingestion.craigslist.fetch_search_rss", fake_fetch)
    listings = fetch_listings("https://example.com/rss")
    assert len(listings) == 2

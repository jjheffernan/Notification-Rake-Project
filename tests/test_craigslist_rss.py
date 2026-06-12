from notification_rake.ingestion.craigslist import parse_rss_items

SAMPLE_RSS = """<?xml version="1.0"?>
<rss><channel>
<item>
  <title>2019 Toyota Camry $12,500</title>
  <link>https://sfbay.craigslist.org/cta/d/sfc/12345.html</link>
  <description>Clean title, low miles</description>
</item>
<item>
  <title>Honda Civic</title>
  <link>https://sfbay.craigslist.org/cta/d/sfc/67890.html</link>
</item>
</channel></rss>"""


def test_parse_rss_items_extracts_listings():
    listings = list(parse_rss_items(SAMPLE_RSS))
    assert len(listings) == 2
    first = listings[0]
    assert first.source == "craigslist"
    assert first.source_listing_id == "12345"
    assert first.title == "2019 Toyota Camry $12,500"
    assert first.price == 12500.0
    assert first.year == 2019


def test_parse_rss_items_skips_items_without_link():
    rss = "<rss><channel><item><title>No link</title></item></channel></rss>"
    assert list(parse_rss_items(rss)) == []

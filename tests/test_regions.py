from notification_rake.models.regions import SOURCE_COUNTRY, country_for_source


def test_country_for_source():
    assert country_for_source("craigslist") == "US"
    assert country_for_source("yahoo_auctions_jp") == "JP"
    assert country_for_source("copart") == "US"
    assert country_for_source("ebay") == "US"
    assert country_for_source("ebay_uk") == "GB"
    assert country_for_source("mobile_de") == "DE"
    assert country_for_source("unknown") is None


def test_source_country_registry():
    assert "craigslist" in SOURCE_COUNTRY
    assert SOURCE_COUNTRY["yahoo_auctions_jp"] == "JP"
    assert SOURCE_COUNTRY["autoscout24_de"] == "DE"

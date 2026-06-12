from notification_rake.ingestion.craigslist import _parse_price, _parse_year


def test_parse_price():
    assert _parse_price("2020 Toyota Camry $12,500") == 12500.0
    assert _parse_price("no price") is None


def test_parse_year():
    assert _parse_year("2019 Honda Civic") == 2019
    assert _parse_year("classic car") is None

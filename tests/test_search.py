from notification_rake.search import (
    VALID_SORT,
    ListingSearch,
    _build_search_sql,
    _sort_clause,
)


def test_valid_sort_keys():
    search = ListingSearch(sort="price_asc")
    assert "vl.price ASC" in _sort_clause(search)


def test_build_search_filters():
    search = ListingSearch(q="camry", make="Toyota", price_max=20000, country="US")
    _, where, params = _build_search_sql(search)
    assert "ILIKE" in where
    assert "mk.name ILIKE" in where
    assert "vl.price <=" in where
    assert "vl.country =" in where
    assert params["q"] == "%camry%"
    assert params["make"] == "Toyota"
    assert params["country"] == "US"


def test_invalid_sort_falls_back():
    search = ListingSearch(sort="not-real")
    assert _sort_clause(search) == "vl.updated_at DESC"
    assert "not-real" not in VALID_SORT

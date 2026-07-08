"""Tests for make/model market analytics."""

from notification_rake.search.market import (
    _sales_kpis,
    classify_sale_status,
    compute_moving_average,
    slug_to_label,
    slugify,
)


def test_slugify():
    assert slugify("Nissan Stagea") == "nissan-stagea"
    assert slugify("BMW M3") == "bmw-m3"


def test_slug_to_label():
    assert slug_to_label("nissan-stagea") == "Nissan Stagea"
    assert slug_to_label("bmw-m3") == "Bmw M3"


def test_classify_sale_status():
    assert classify_sale_status("sold") == "sold"
    assert classify_sale_status("live") == "high_bid"
    assert classify_sale_status(None, price_events=3) == "last_asking"
    assert classify_sale_status(None) == "for_sale"


def test_compute_moving_average():
    points = [
        {"date": "2025-01-15", "price": 10000, "status": "sold"},
        {"date": "2025-02-10", "price": 20000, "status": "sold"},
        {"date": "2025-03-05", "price": 30000, "status": "sold"},
    ]
    avg = compute_moving_average(points, window_months=2)
    assert len(avg) == 3
    assert avg[-1]["avg_price"] == 25000


def test_sales_kpis():
    points = [
        {"date": "2025-01-01", "price": 10000, "status": "sold"},
        {"date": "2025-02-01", "price": 30000, "status": "sold"},
    ]
    kpis = _sales_kpis(points)
    assert kpis["sales_count"] == 2
    assert kpis["avg_price"] == 20000
    assert kpis["dollar_volume"] == 40000
    assert kpis["lowest_sale"] == 10000
    assert kpis["top_sale"] == 30000

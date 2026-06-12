from unittest.mock import patch

from notification_rake.models import VehicleListing
from notification_rake.notifications import format_listing_message, notify_new_listings


def test_format_listing_message():
    listing = VehicleListing(
        source="c",
        source_listing_id="1",
        title="2019 Toyota Camry LE",
        price=12500.0,
        year=2019,
        make="Toyota",
        model="Camry",
    )
    msg = format_listing_message(listing)
    assert "2019 Toyota Camry LE" in msg
    assert "12,500" in msg
    assert "Toyota Camry" in msg


def test_notify_new_listings():
    items = [
        VehicleListing(source="c", source_listing_id="1", title="A"),
        VehicleListing(source="c", source_listing_id="2", title="B"),
    ]
    with patch("notification_rake.notifications.alerts.send_alert") as mock_send:
        count = notify_new_listings(items)
    assert count == 2
    assert mock_send.call_count == 2

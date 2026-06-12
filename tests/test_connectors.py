from notification_rake.ingestion.connectors import ConnectorConfig, fetch_from_connector
from notification_rake.web.media_proxy import is_allowed_image_url, proxy_url_for


def test_ebay_connector_fixture():
    cfg = ConnectorConfig(provider="ebay", label="mine", config={"query": "supra"})
    items = fetch_from_connector(cfg)
    assert len(items) == 1
    assert items[0].source == "ebay"


def test_image_proxy_allowlist():
    assert is_allowed_image_url("https://cs.copart.com/v1/photo.jpg")
    assert not is_allowed_image_url("https://evil.example/photo.jpg")


def test_proxy_url_for():
    assert proxy_url_for("https://cs.copart.com/x.jpg").startswith("/api/images/proxy?url=")

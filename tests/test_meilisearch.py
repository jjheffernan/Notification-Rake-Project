from unittest.mock import MagicMock, patch

import httpx

from notification_rake.config import settings
from notification_rake.search import ListingSearch
from notification_rake.search import meilisearch_client as meili


def test_meilisearch_enabled_auto():
    with patch.object(settings, "meilisearch_url", "http://meilisearch:7700"):
        with patch.object(settings, "search_engine", "auto"):
            assert meili.meilisearch_enabled() is True


def test_build_filters_includes_country():
    search = ListingSearch(country="JP", make="Nissan")
    filters = meili._build_filters(search)
    assert 'country = "JP"' in filters
    assert 'make = "Nissan"' in filters


def test_search_documents_parses_hits():
    search = ListingSearch(q="camry", limit=10, offset=0)
    response = httpx.Response(
        200,
        json={"hits": [{"id": "abc-123"}], "estimatedTotalHits": 1},
        request=httpx.Request("POST", "http://test/indexes/listings/search"),
    )

    with patch.object(settings, "meilisearch_url", "http://test"):
        with patch.object(settings, "meilisearch_api_key", ""):
            with patch.object(meili, "_client") as client_factory:
                client = MagicMock()
                client.__enter__.return_value = client
                client.post.return_value = response
                client_factory.return_value = client
                ids, total = meili.search_documents(search)

    assert ids == ["abc-123"]
    assert total == 1

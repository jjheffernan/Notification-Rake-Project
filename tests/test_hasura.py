from unittest.mock import patch

import httpx

from notification_rake.integrations.hasura import TRACKED_TABLES, track_tables


def test_track_tables():
    ok = httpx.Response(
        200,
        request=httpx.Request("POST", "http://hasura:8080/v1/metadata"),
    )
    with patch.object(httpx.Client, "post", return_value=ok) as mock_post:
        tracked = track_tables(
            hasura_url="http://hasura:8080",
            admin_secret="secret",
        )
    assert tracked == [f"{schema}.{table}" for schema, table in TRACKED_TABLES]
    assert mock_post.call_count == len(TRACKED_TABLES)

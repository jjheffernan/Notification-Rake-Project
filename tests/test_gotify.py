from unittest.mock import patch

import httpx

import notification_rake.integrations.gotify as gotify


def test_send_alert_skips_without_token(monkeypatch):
    monkeypatch.setattr(gotify.settings, "gotify_token", "")
    with patch.object(httpx.Client, "post") as mock_post:
        gotify.send_alert("t", "m")
        mock_post.assert_not_called()


def test_send_alert_posts_to_gotify(monkeypatch):
    monkeypatch.setattr(gotify.settings, "gotify_token", "app-token")
    monkeypatch.setattr(gotify.settings, "gotify_url", "http://gotify:80")

    ok = httpx.Response(
        200,
        request=httpx.Request("POST", "http://gotify:80/message"),
    )
    with patch.object(httpx.Client, "post", return_value=ok) as mock_post:
        gotify.send_alert("New listing", "2020 Camry $12k")
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["params"]["token"] == "app-token"
        assert kwargs["json"]["title"] == "New listing"

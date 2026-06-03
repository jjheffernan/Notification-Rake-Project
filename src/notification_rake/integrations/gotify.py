"""Gotify push alerts."""

from __future__ import annotations

import httpx

from notification_rake.config import settings


def send_alert(title: str, message: str, priority: int = 5) -> None:
    """POST to Gotify; no-op if GOTIFY_TOKEN unset."""
    if not settings.gotify_token:
        return
    url = f"{settings.gotify_url.rstrip('/')}/message"
    with httpx.Client(timeout=15.0) as client:
        client.post(
            url,
            params={"token": settings.gotify_token},
            json={"title": title, "message": message, "priority": priority},
        ).raise_for_status()

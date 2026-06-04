"""Hotlink image proxy — stream remote URLs, no local persistence."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from notification_rake.config import settings


def is_allowed_image_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    allowed = settings.image_proxy_hosts
    if not allowed:
        return True
    return any(host == h or host.endswith(f".{h}") for h in allowed)


def proxy_image(url: str) -> tuple[bytes, str]:
    if not is_allowed_image_url(url):
        raise ValueError("image host not allowed")
    headers = {"User-Agent": settings.geocode_user_agent, "Accept": "image/*,*/*"}
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/jpeg")
        return resp.content, content_type


def proxy_url_for(source_url: str) -> str:
    from urllib.parse import quote

    return f"/api/images/proxy?url={quote(source_url, safe='')}"

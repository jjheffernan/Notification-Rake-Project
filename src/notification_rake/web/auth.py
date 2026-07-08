"""Admin session helpers for the dashboard."""

from __future__ import annotations

import secrets

from notification_rake.config import settings

_CSRF_SESSION_KEY = "_admin_csrf"


def ensure_csrf_token(session: dict[str, object]) -> str:
    token = session.get(_CSRF_SESSION_KEY)
    if not isinstance(token, str):
        token = secrets.token_urlsafe(32)
        session[_CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(session: dict[str, object], submitted: str | None) -> bool:
    expected = session.get(_CSRF_SESSION_KEY)
    if not isinstance(expected, str) or not submitted:
        return False
    return secrets.compare_digest(submitted, expected)


def verify_admin(username: str, password: str) -> bool:
    return (
        username == settings.admin_user
        and password == settings.admin_password
        and bool(settings.admin_password)
    )


def is_admin_session(session: dict[str, object]) -> bool:
    return session.get("admin") is True and session.get("user") == settings.admin_user

"""Admin session helpers for the dashboard."""

from __future__ import annotations

from notification_rake.config import settings


def verify_admin(username: str, password: str) -> bool:
    return (
        username == settings.admin_user
        and password == settings.admin_password
        and bool(settings.admin_password)
    )


def is_admin_session(session: dict[str, object]) -> bool:
    return session.get("admin") is True and session.get("user") == settings.admin_user

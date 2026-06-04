"""Session flash helpers."""

from __future__ import annotations

from flask import abort, session

from notification_rake.web.auth import is_admin_session


def admin_guard() -> None:
    if not is_admin_session(session):
        abort(401)


def set_flash(message: str, *, ok: bool = True) -> None:
    session["flash"] = {"ok": ok, "message": message}


def pop_flash() -> dict[str, object] | None:
    flash = session.pop("flash", None)
    return flash if isinstance(flash, dict) else None

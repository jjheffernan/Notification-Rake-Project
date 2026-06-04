"""Admin runtime console routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from notification_rake.admin import (
    add_catalog_model,
    admin_overview,
    execute_action,
    set_source_enabled,
)
from notification_rake.config import settings
from notification_rake.web.auth import is_admin_session, verify_admin
from notification_rake.web.helpers import admin_guard, pop_flash, set_flash

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/login")
def admin_login_page():
    if is_admin_session(session):
        return redirect(url_for("admin.admin_home"), code=303)
    return render_template("admin_login.html")


@bp.post("/login")
def admin_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    if not verify_admin(username, password):
        return render_template("admin_login.html", error="Invalid credentials"), 401
    session["admin"] = True
    session["user"] = username
    return redirect(url_for("admin.admin_home"), code=303)


@bp.post("/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("public.dashboard"), code=303)


@bp.get("/")
def admin_home():
    if not is_admin_session(session):
        return redirect(url_for("admin.admin_login_page"), code=303)
    overview = admin_overview()
    return render_template("admin.html", overview=overview, flash=pop_flash())


@bp.get("/api/overview")
def admin_api_overview():
    admin_guard()
    return jsonify(admin_overview())


@bp.post("/api/actions/<action>")
def admin_run_action(action: str):
    admin_guard()
    result = execute_action(action)
    return jsonify(ok=result.ok, action=result.action, message=result.message)


@bp.post("/actions/<action>")
def admin_run_action_form(action: str):
    if not is_admin_session(session):
        return redirect(url_for("admin.admin_login_page"), code=303)
    result = execute_action(action)
    set_flash(result.message, ok=result.ok)
    return redirect(url_for("admin.admin_home"), code=303)


@bp.post("/sources/<int:source_id>/toggle")
def admin_toggle_source(source_id: int):
    if not is_admin_session(session):
        return redirect(url_for("admin.admin_login_page"), code=303)
    enabled = request.form.get("enabled", "").lower() == "true"
    set_source_enabled(settings.database_url, source_id, enabled=enabled)
    state = "enabled" if enabled else "disabled"
    set_flash(f"Source #{source_id} {state}.", ok=True)
    return redirect(url_for("admin.admin_home"), code=303)


@bp.post("/catalog")
def admin_add_catalog():
    if not is_admin_session(session):
        return redirect(url_for("admin.admin_login_page"), code=303)
    make = request.form.get("make", "")
    model = request.form.get("model", "")
    result = add_catalog_model(settings.database_url, make, model)
    set_flash(result.message, ok=result.ok)
    return redirect(url_for("admin.admin_home"), code=303)

"""Flask application factory."""

from __future__ import annotations

import time
from pathlib import Path

from flask import Flask, request

from notification_rake.config import configure_logging, settings
from notification_rake.storage.metadata import record_api_usage
from notification_rake.web.blueprints.admin import bp as admin_bp
from notification_rake.web.blueprints.public import bp as public_bp
from notification_rake.web.rate_limit import register_rate_limit

_WEB_ROOT = Path(__file__).resolve().parent


def create_app() -> Flask:
    configure_logging()
    app = Flask(
        __name__,
        template_folder=str(_WEB_ROOT / "templates"),
        static_folder=str(_WEB_ROOT / "static"),
    )
    app.secret_key = settings.dashboard_secret_key
    app.config["APPLICATION_ROOT"] = "/"
    app.url_map.strict_slashes = False
    if settings.rake_env.lower() == "production":
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["SESSION_COOKIE_HTTPONLY"] = True
        app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    register_rate_limit(app)

    @app.context_processor
    def inject_nav_context():
        return {"admin_nav_visible": settings.admin_nav_visible}

    @app.after_request
    def track_api_usage(response):
        if request.path.startswith("/api/"):
            start = request.environ.get("_start_time")
            duration_ms = int((time.perf_counter() - start) * 1000) if start else 0
            try:
                record_api_usage(
                    settings.database_url,
                    endpoint=request.path,
                    method=request.method,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
            except Exception:
                pass
        return response

    @app.before_request
    def _mark_start():
        request.environ["_start_time"] = time.perf_counter()

    return app


app = create_app()

"""Flask application factory."""

from __future__ import annotations

import time
from pathlib import Path

from flask import Flask, request

from notification_rake.config import settings
from notification_rake.storage.metadata import record_api_usage
from notification_rake.web.blueprints.admin import bp as admin_bp
from notification_rake.web.blueprints.public import bp as public_bp

_WEB_ROOT = Path(__file__).resolve().parent


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(_WEB_ROOT / "templates"),
        static_folder=str(_WEB_ROOT / "static"),
    )
    app.secret_key = settings.dashboard_secret_key
    app.config["APPLICATION_ROOT"] = "/"
    app.url_map.strict_slashes = False

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

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

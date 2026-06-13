"""Add a make/model to the vehicle catalog."""

from __future__ import annotations

import os
import sys

from notification_rake.config import settings
from notification_rake.storage import add_vehicle_model

ALIASES = ("add_model",)


def run() -> int:
    make = os.environ.get("MAKE", "").strip()
    model = os.environ.get("MODEL", "").strip()
    if not make or not model:
        print("usage: MAKE=Toyota MODEL=Supra notification-rake add_model", file=sys.stderr)
        return 2
    model_id = add_vehicle_model(settings.database_url, make, model)
    print(f"add_model: {make}/{model} -> model_id={model_id}")
    return 0

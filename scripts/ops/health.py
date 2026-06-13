"""Check db, hasura, gotify reachability."""

from __future__ import annotations

from notification_rake.admin import check_services

ALIASES = ("health",)


def run() -> int:
    ok = True
    for svc in check_services():
        print(f"{svc.key}: {svc.status} ({svc.detail})")
        if svc.status == "fail":
            ok = False
    return 0 if ok else 1

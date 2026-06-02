"""Auction metadata analysis — damage, title, mobility (no VIN decode)."""

from __future__ import annotations

from typing import Any, Protocol


class AuctionLike(Protocol):
    primary_damage: str | None
    secondary_damage: str | None
    title_type: str | None
    run_and_drive: bool | None
    has_keys: bool | None
    loss_type: str | None


_DAMAGE_SEVERITY: dict[str, int] = {
    "MINOR DENT/SCRATCHES": 1,
    "NORMAL WEAR": 1,
    "HAIL": 2,
    "REAR END": 3,
    "SIDE": 3,
    "FRONT END": 4,
    "ROLLOVER": 5,
    "BURN": 5,
    "FLOOD": 5,
    "WATER/FLOOD": 5,
}


def normalize_damage(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().upper().replace("_", " ")


def damage_severity(primary: str | None, secondary: str | None = None) -> int:
    scores = [
        _DAMAGE_SEVERITY.get(normalize_damage(d) or "", 2) for d in (primary, secondary) if d
    ]
    return max(scores) if scores else 1


def normalize_title_type(value: str | None) -> str | None:
    if not value:
        return None
    upper = value.strip().upper()
    if "CLEAN" in upper:
        return "clean"
    if "NON" in upper and "REPAIR" in upper:
        return "non_repairable"
    if "SALVAGE" in upper or "REBUILD" in upper:
        return "salvage"
    return upper.lower()


def mobility_score(*, run_and_drive: bool | None, has_keys: bool | None, severity: int) -> int:
    score = 3
    if run_and_drive:
        score += 2
    if has_keys:
        score += 1
    score -= max(0, severity - 2)
    return max(1, min(5, score))


def analyze_copart_lot(lot: AuctionLike) -> dict[str, Any]:
    primary = normalize_damage(lot.primary_damage)
    secondary = normalize_damage(lot.secondary_damage)
    severity = damage_severity(primary, secondary)
    title = normalize_title_type(lot.title_type)
    mobility = mobility_score(
        run_and_drive=lot.run_and_drive,
        has_keys=lot.has_keys,
        severity=severity,
    )
    badges: list[str] = []
    if primary:
        badges.append(primary.title())
    if title:
        badges.append(title.replace("_", " ").title())
    if lot.run_and_drive:
        badges.append("Runs & drives")
    elif lot.run_and_drive is False:
        badges.append("Does not run")
    if lot.has_keys:
        badges.append("Keys")
    elif lot.has_keys is False:
        badges.append("No keys")
    return {
        "primary_damage": primary,
        "secondary_damage": secondary,
        "damage_severity": severity,
        "title_type": title,
        "mobility_score": mobility,
        "loss_type": (lot.loss_type or "").upper() or None,
        "badges": badges,
    }


def analyze_yahoo_hit(title: str, *, ends_soon_hours: int | None = None) -> dict[str, Any]:
    badges: list[str] = ["Yahoo Auction"]
    if ends_soon_hours is not None and ends_soon_hours <= 24:
        badges.append("Ending soon")
    return {"badges": badges, "title_tokens": title[:120]}

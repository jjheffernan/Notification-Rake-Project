"""Map messy listing titles to canonical make/model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from notification_rake.models.listing import VehicleListing

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


@dataclass(frozen=True)
class ModelRef:
    make_id: int
    make: str
    model_id: int
    model: str


FALLBACK_CATALOG: tuple[ModelRef, ...] = (
    ModelRef(1, "Toyota", 1, "Camry"),
    ModelRef(1, "Toyota", 2, "Corolla"),
    ModelRef(1, "Toyota", 3, "RAV4"),
    ModelRef(2, "Honda", 4, "Civic"),
    ModelRef(2, "Honda", 5, "Accord"),
    ModelRef(3, "Ford", 6, "F-150"),
    ModelRef(4, "Nissan", 7, "Altima"),
    ModelRef(4, "Nissan", 8, "Stagea"),
)


def load_catalog_from_db(dsn: str) -> list[ModelRef]:
    import psycopg

    sql = """
        SELECT mk.id, mk.name, mo.id, mo.name
        FROM vehicle_make mk
        JOIN vehicle_model mo ON mo.make_id = mk.id
        ORDER BY mk.name, mo.name
    """
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql).fetchall()
    return [ModelRef(int(mk_id), make, int(mo_id), model) for mk_id, make, mo_id, model in rows]


def load_catalog(dsn: str | None = None) -> list[ModelRef]:
    """Postgres catalog when DSN works; bundled fallback only when DB is unreachable."""
    if dsn:
        try:
            return load_catalog_from_db(dsn)
        except OSError:
            pass
    return list(FALLBACK_CATALOG)


def find_model_ref(title: str, catalog: list[ModelRef]) -> ModelRef | None:
    """Best make/model match for a listing title."""
    text = (title or "").lower()
    if not text:
        return None

    best: tuple[ModelRef, float] | None = None
    for ref in catalog:
        make_l, model_l = ref.make.lower(), ref.model.lower()
        if model_l not in text and _similarity(model_l, text) < 0.75:
            continue
        score = 1.0 if model_l in text else _similarity(model_l, text)
        if make_l in text:
            score += 0.25
        if best is None or score > best[1]:
            best = (ref, score)

    if best and best[1] >= 0.75:
        return best[0]
    return None


def normalize_listing(listing: VehicleListing, catalog: list[ModelRef]) -> VehicleListing:
    ref = find_model_ref(listing.title or "", catalog)
    if not ref:
        return listing
    return listing.model_copy(update={"make": ref.make, "model": ref.model})


def normalize_listings(
    listings: list[VehicleListing], catalog: list[ModelRef]
) -> list[VehicleListing]:
    return [normalize_listing(item, catalog) for item in listings]


def lookup_ids(
    make: str | None, model: str | None, catalog: list[ModelRef]
) -> tuple[int | None, int | None]:
    if not make or not model:
        return None, None
    for ref in catalog:
        if ref.make.lower() == make.lower() and ref.model.lower() == model.lower():
            return ref.make_id, ref.model_id
    return None, None


def _similarity(needle: str, haystack: str) -> float:
    if needle in haystack:
        return 1.0
    return max(SequenceMatcher(None, needle, haystack).ratio(), 0.0)


def parse_year(text: str) -> int | None:
    match = YEAR_RE.search(text)
    return int(match.group()) if match else None

"""Copart lot detail fetch."""

from __future__ import annotations

from notification_rake.ingestion.copart.client import CopartClient, load_sample_lots
from notification_rake.ingestion.copart.search import CopartLot, _parse_lot


def fetch_lot_detail(lot_number: str, *, client: CopartClient | None = None) -> CopartLot | None:
    client = client or CopartClient.from_settings()
    if client.use_fixture():
        raw = load_sample_lots()
        for row in raw.get("items") or []:
            if str(row.get("lot_number")) == str(lot_number):
                return _parse_lot(row)
        return None
    data = client.get_json(f"lots/{lot_number}")
    row = data.get("lot") or data.get("item") or data
    if not isinstance(row, dict):
        return None
    return _parse_lot(row)

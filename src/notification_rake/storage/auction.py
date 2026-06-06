"""Sync auction_lot rows from ingested listings."""

from __future__ import annotations

import json
from typing import Any

from notification_rake.models.listing import VehicleListing


def sync_auction_lot(dsn: str, listing_id: str, item: VehicleListing) -> None:
    import psycopg

    meta = item.metadata or {}
    platform = meta.get("platform") or item.source
    lot_number = meta.get("lot_number") or meta.get("auction_id") or item.source_listing_id
    if platform not in {"copart", "yahoo_auctions_jp"}:
        return

    analysis = meta.get("analysis") or {}
    sql = """
        INSERT INTO listings.auction_lot (
            listing_id, platform, lot_number, auction_status, ends_at,
            primary_damage, secondary_damage, loss_type,
            run_and_drive, has_keys, title_type, bid_count, analysis
        ) VALUES (
            %(listing_id)s::uuid, %(platform)s, %(lot_number)s, %(auction_status)s, %(ends_at)s,
            %(primary_damage)s, %(secondary_damage)s, %(loss_type)s,
            %(run_and_drive)s, %(has_keys)s, %(title_type)s, %(bid_count)s, %(analysis)s::jsonb
        )
        ON CONFLICT (platform, lot_number) DO UPDATE SET
            listing_id = EXCLUDED.listing_id,
            auction_status = EXCLUDED.auction_status,
            ends_at = EXCLUDED.ends_at,
            primary_damage = EXCLUDED.primary_damage,
            secondary_damage = EXCLUDED.secondary_damage,
            loss_type = EXCLUDED.loss_type,
            run_and_drive = EXCLUDED.run_and_drive,
            has_keys = EXCLUDED.has_keys,
            title_type = EXCLUDED.title_type,
            bid_count = EXCLUDED.bid_count,
            analysis = EXCLUDED.analysis;
    """
    ends_at = meta.get("auction_date") or meta.get("ends_at")
    params = {
        "listing_id": listing_id,
        "platform": platform,
        "lot_number": str(lot_number),
        "auction_status": meta.get("auction_status"),
        "ends_at": ends_at,
        "primary_damage": meta.get("primary_damage") or analysis.get("primary_damage"),
        "secondary_damage": meta.get("secondary_damage") or analysis.get("secondary_damage"),
        "loss_type": meta.get("loss_type") or analysis.get("loss_type"),
        "run_and_drive": meta.get("run_and_drive"),
        "has_keys": meta.get("has_keys"),
        "title_type": meta.get("title_type") or analysis.get("title_type"),
        "bid_count": meta.get("bid_count"),
        "analysis": json.dumps(analysis),
    }
    with psycopg.connect(dsn) as conn:
        conn.execute(sql, params)
        conn.commit()


def auction_detail_for_listing(dsn: str, listing_id: str) -> dict[str, Any] | None:
    import psycopg

    sql = """
        SELECT al.platform, al.lot_number, al.auction_status, al.ends_at,
               al.primary_damage, al.secondary_damage, al.loss_type,
               al.run_and_drive, al.has_keys, al.title_type, al.bid_count, al.analysis
        FROM listings.auction_lot al
        JOIN listings.listing rl ON rl.id = al.listing_id
        JOIN listings.source src ON src.id = rl.source_id
        JOIN public.vehicle_listing vl ON vl.source_listing_id = rl.external_id
            AND vl.source = src.name
        WHERE vl.id = %(id)s::uuid;
    """
    with psycopg.connect(dsn) as conn:
        row = conn.execute(sql, {"id": listing_id}).fetchone()
    if not row:
        return None
    analysis = row[11]
    if not isinstance(analysis, dict):
        analysis = json.loads(analysis or "{}")
    return {
        "platform": row[0],
        "lot_number": row[1],
        "auction_status": row[2],
        "ends_at": row[3].isoformat() if row[3] else None,
        "primary_damage": row[4],
        "secondary_damage": row[5],
        "loss_type": row[6],
        "run_and_drive": row[7],
        "has_keys": row[8],
        "title_type": row[9],
        "bid_count": row[10],
        "analysis": analysis,
        "badges": analysis.get("badges") or [],
    }


def list_images_for_listing(dsn: str, listing_id: str) -> list[dict[str, Any]]:
    import psycopg

    sql = """
        SELECT li.url, li.position
        FROM listings.listing_image li
        JOIN listings.listing rl ON rl.id = li.listing_id
        JOIN listings.source src ON src.id = rl.source_id
        JOIN public.vehicle_listing vl ON vl.source_listing_id = rl.external_id
            AND vl.source = src.name
        WHERE vl.id = %(id)s::uuid
        ORDER BY li.position;
    """
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(sql, {"id": listing_id}).fetchall()
    return [{"url": r[0], "position": int(r[1])} for r in rows]

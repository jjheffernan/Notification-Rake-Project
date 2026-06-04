"""Public dashboard + listing search API."""

from __future__ import annotations

import uuid

from flask import Blueprint, abort, jsonify, make_response, render_template, request

from notification_rake.config import settings
from notification_rake.ingestion.connectors import SUPPORTED_PROVIDERS
from notification_rake.search import (
    ListingSearch,
    get_listing_detail,
    list_ingest_routes,
    list_regions,
    market_summary,
    search_facets,
    search_listings,
)
from notification_rake.search.market import (
    ModelMarketQuery,
    list_model_markets,
    model_market_detail,
    resolve_model_from_slugs,
)
from notification_rake.storage.accounts import (
    delete_account,
    list_accounts,
    new_profile_id,
    upsert_account,
)
from notification_rake.storage.scheduled_searches import (
    ScheduledSearch,
    delete_scheduled_search,
    list_scheduled_searches,
    upsert_scheduled_search,
)
from notification_rake.web.media_proxy import proxy_image

bp = Blueprint("public", __name__)

ACCOUNT_FIELDS: dict[str, list[str]] = {
    "craigslist": ["rss_url"],
    "yahoo_auctions_jp": ["query", "max_pages"],
    "buyee": ["query", "watchlist_query", "member_id"],
    "ebay": ["api_key", "oauth_token", "query", "limit", "marketplace"],
    "ebay_uk": ["api_key", "oauth_token", "query", "limit", "marketplace"],
    "ebay_de": ["api_key", "oauth_token", "query", "limit", "marketplace"],
    "copart": ["query", "state", "limit"],
    "copart_uk": ["query", "limit"],
    "copart_de": ["query", "limit"],
    "gumtree": ["query", "limit"],
    "autoscout24_uk": ["query", "limit"],
    "autoscout24_de": ["query", "limit"],
    "mobile_de": ["query", "limit"],
    "carsandbids": ["query", "mode", "limit"],
}


@bp.get("/")
def dashboard():
    from notification_rake.models.regions import REGION_CENTERS, REGION_LABELS

    regions = [
        {
            "code": code,
            "label": label,
            "lat": REGION_CENTERS[code][1],
            "lon": REGION_CENTERS[code][0],
        }
        for code, label in REGION_LABELS.items()
    ]
    return render_template(
        "dashboard.html",
        title="Vehicle Listings",
        nav_active="search",
        default_lat=settings.default_lat,
        default_lon=settings.default_lon,
        regions=regions,
    )


@bp.get("/accounts")
def accounts_page():
    return render_template(
        "accounts.html",
        title="Connected Accounts — Notification Rake",
        nav_active="accounts",
        account_providers=sorted(SUPPORTED_PROVIDERS),
    )


@bp.get("/watchlist")
def watchlist_page():
    return render_template(
        "watchlist.html",
        title="Watchlist — Notification Rake",
        nav_active="watchlist",
    )


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.get("/m")
def market_index():
    return render_template(
        "market_index.html",
        title="Market Data — Notification Rake",
        nav_active="market",
    )


@bp.get("/m/<make_slug>/<model_slug>")
def market_model(make_slug: str, model_slug: str):
    resolved = resolve_model_from_slugs(settings.database_url, make_slug, model_slug)
    if not resolved:
        abort(404, description="model not found")
    return render_template(
        "market_model.html",
        title=f"{resolved.make} {resolved.model} — Market Data",
        nav_active="market",
        make_label=resolved.make,
        model_label=resolved.model,
        make_slug=make_slug,
        model_slug=model_slug,
    )


@bp.get("/api/market/models")
def api_market_models():
    limit = min(max(request.args.get("limit", 100, type=int), 1), 500)
    models = list_model_markets(settings.database_url, limit=limit)
    return _cached_json({"models": models, "total": len(models)}, max_age=120)


@bp.get("/api/market/model")
def api_market_model():
    make = request.args.get("make") or ""
    model = request.args.get("model") or ""
    if not make or not model:
        abort(400, description="make and model required")
    query = ModelMarketQuery(
        make=make,
        model=model,
        year_min=request.args.get("year_min", type=int),
        year_max=request.args.get("year_max", type=int),
        source=request.args.get("source") or None,
        country=request.args.get("country") or None,
    )
    detail = model_market_detail(settings.database_url, query)
    if not detail:
        abort(404, description="no market data for this model")
    return _cached_json(detail, max_age=120)


@bp.get("/api/market/<make_slug>/<model_slug>")
def api_market_model_slug(make_slug: str, model_slug: str):
    resolved = resolve_model_from_slugs(settings.database_url, make_slug, model_slug)
    if not resolved:
        abort(404, description="model not found")
    query = ModelMarketQuery(
        make=resolved.make,
        model=resolved.model,
        year_min=request.args.get("year_min", type=int),
        year_max=request.args.get("year_max", type=int),
        source=request.args.get("source") or None,
        country=request.args.get("country") or None,
    )
    detail = model_market_detail(settings.database_url, query)
    if not detail:
        abort(404, description="no market data for this model")
    return _cached_json(detail, max_age=120)


def _cached_json(payload, *, max_age: int = 60):
    resp = make_response(jsonify(payload))
    resp.headers["Cache-Control"] = f"public, max-age={max_age}"
    return resp


@bp.get("/api/routes")
def api_ingest_routes():
    return _cached_json({"routes": list_ingest_routes(settings.database_url)}, max_age=120)


@bp.get("/api/market/summary")
def api_market_summary():
    return _cached_json(market_summary(settings.database_url), max_age=120)


@bp.get("/api/regions")
def api_regions():
    return _cached_json({"regions": list_regions(settings.database_url)}, max_age=120)


@bp.get("/api/facets")
def api_facets():
    search = _search_from_args(include_sort=False)
    return _cached_json(search_facets(settings.database_url, search))


@bp.get("/api/listings/<listing_id>")
def api_listing_detail(listing_id: str):
    detail = get_listing_detail(settings.database_url, listing_id)
    if not detail:
        abort(404, description="listing not found")
    return _cached_json(detail, max_age=300)


@bp.get("/api/listings")
def api_listings():
    limit = min(max(request.args.get("limit", 24, type=int), 1), 100)
    offset = max(request.args.get("offset", 0, type=int), 0)
    search = _search_from_args(limit=limit, offset=offset)
    items, total = search_listings(settings.database_url, search)
    from notification_rake.web.media_proxy import proxy_url_for

    for item in items:
        if item.get("thumbnail_url"):
            item["thumbnail_proxy"] = proxy_url_for(item["thumbnail_url"])
    return _cached_json({"items": items, "total": total, "limit": limit, "offset": offset})


@bp.get("/api/images/proxy")
def api_image_proxy():
    if not settings.image_proxy_enabled:
        abort(404)
    url = request.args.get("url", "")
    if not url:
        abort(400, description="url required")
    try:
        content, content_type = proxy_image(url)
    except ValueError as exc:
        abort(403, description=str(exc))
    except Exception as exc:
        abort(502, description=str(exc))
    resp = make_response(content)
    resp.headers["Content-Type"] = content_type
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


@bp.post("/api/profile")
def api_create_profile():
    return jsonify(profile_id=new_profile_id())


@bp.get("/api/accounts")
def api_list_accounts():
    profile_id = request.args.get("profile_id")
    if not profile_id:
        abort(400, description="profile_id required")
    try:
        uuid.UUID(profile_id)
    except ValueError:
        abort(400, description="invalid profile_id")
    accounts = list_accounts(settings.database_url, profile_id)
    return jsonify(
        accounts=[
            {
                "id": a.id,
                "provider": a.provider,
                "label": a.label,
                "enabled": a.enabled,
                "last_sync_at": a.last_sync_at,
                "last_status": a.last_status,
                "listings_synced": a.listings_synced,
                "fields": ACCOUNT_FIELDS.get(a.provider, []),
            }
            for a in accounts
        ]
    )


@bp.post("/api/accounts")
def api_connect_account():
    body = request.get_json(silent=True) or {}
    profile_id = body.get("profile_id")
    provider = body.get("provider")
    if not profile_id or not provider:
        abort(400, description="profile_id and provider required")
    config = body.get("config") or {}
    label = body.get("label") or provider
    try:
        account = upsert_account(
            settings.database_url,
            profile_id=profile_id,
            provider=provider,
            label=label,
            config=config,
            enabled=bool(body.get("enabled", True)),
        )
    except ValueError as exc:
        abort(400, description=str(exc))
    return jsonify(
        id=account.id,
        provider=account.provider,
        label=account.label,
        enabled=account.enabled,
    )


@bp.delete("/api/accounts/<account_id>")
def api_disconnect_account(account_id: str):
    profile_id = request.args.get("profile_id")
    if not profile_id:
        abort(400, description="profile_id required")
    if not delete_account(settings.database_url, account_id, profile_id):
        abort(404)
    return jsonify(ok=True)


@bp.post("/api/accounts/sync")
def api_sync_accounts():
    body = request.get_json(silent=True) or {}
    profile_id = body.get("profile_id")
    if not profile_id:
        abort(400, description="profile_id required")
    from notification_rake.workflow.multi_source import run_connected_sync

    result = run_connected_sync(profile_id)
    return jsonify(
        upserted=result.upserted,
        connected=result.connected,
        by_source=result.by_source,
    )


def _scheduled_search_json(search: ScheduledSearch) -> dict:
    return {
        "id": search.id,
        "profile_id": search.profile_id,
        "name": search.name,
        "query_json": search.query_json,
        "alert_enabled": search.alert_enabled,
        "enabled": search.enabled,
        "interval_minutes": search.interval_minutes,
        "ingest_routes": search.ingest_routes,
        "last_run_at": search.last_run_at,
        "next_run_at": search.next_run_at,
        "last_match_count": search.last_match_count,
        "last_new_count": search.last_new_count,
        "created_at": search.created_at,
    }


def _validate_profile_id(profile_id: str | None) -> str:
    if not profile_id:
        abort(400, description="profile_id required")
    try:
        uuid.UUID(profile_id)
    except ValueError:
        abort(400, description="invalid profile_id")
    return profile_id


@bp.get("/api/scheduled-searches")
def api_list_scheduled_searches():
    profile_id = _validate_profile_id(request.args.get("profile_id"))
    searches = list_scheduled_searches(settings.database_url, profile_id=profile_id)
    return jsonify(searches=[_scheduled_search_json(s) for s in searches])


@bp.post("/api/scheduled-searches")
def api_upsert_scheduled_search():
    body = request.get_json(silent=True) or {}
    profile_id = _validate_profile_id(body.get("profile_id"))
    query_json = body.get("query_json")
    if not isinstance(query_json, dict):
        abort(400, description="query_json object required")
    name = (body.get("name") or "").strip()
    if not name:
        abort(400, description="name required")
    try:
        search = upsert_scheduled_search(
            settings.database_url,
            profile_id=profile_id,
            name=name,
            query_json=query_json,
            alert_enabled=bool(body.get("alert_enabled", True)),
            enabled=bool(body.get("enabled", True)),
            interval_minutes=int(
                body.get("interval_minutes") or settings.scheduled_search_default_interval_min
            ),
            ingest_routes=body.get("ingest_routes") or [],
            search_id=body.get("id"),
        )
    except (TypeError, ValueError) as exc:
        abort(400, description=str(exc))
    return jsonify(_scheduled_search_json(search))


@bp.delete("/api/scheduled-searches/<search_id>")
def api_delete_scheduled_search(search_id: str):
    profile_id = _validate_profile_id(request.args.get("profile_id"))
    if not delete_scheduled_search(settings.database_url, search_id, profile_id):
        abort(404)
    return jsonify(ok=True)


@bp.post("/api/scheduled-searches/run")
def api_run_scheduled_searches():
    body = request.get_json(silent=True) or {}
    profile_id = body.get("profile_id")
    force = bool(body.get("force"))
    search_id = body.get("search_id")
    validated_profile: str | None = None
    if profile_id:
        validated_profile = _validate_profile_id(profile_id)
    if search_id and validated_profile:
        from notification_rake.storage.scheduled_searches import get_scheduled_search

        one = get_scheduled_search(settings.database_url, search_id)
        if not one or one.profile_id != validated_profile:
            abort(404, description="scheduled search not found")
    from notification_rake.workflow.scheduled_batch import run_scheduled_batch

    result = run_scheduled_batch(
        force=force,
        search_id=search_id,
        profile_id=validated_profile,
        track_job=not search_id,
    )
    return jsonify(
        searches_run=result.searches_run,
        total_new_matches=result.total_new_matches,
        total_alerted=result.total_alerted,
        ingest_upserted=result.ingest_upserted,
        ingest_routes=result.ingest_routes,
        outcomes=[
            {
                "search_id": o.search_id,
                "name": o.name,
                "match_count": o.match_count,
                "new_count": o.new_count,
                "alerted": o.alerted,
                "error": o.error,
            }
            for o in result.outcomes
        ],
    )


def _search_from_args(
    *,
    limit: int = 24,
    offset: int = 0,
    include_sort: bool = True,
) -> ListingSearch:
    radius_m = request.args.get("radius_m", type=float)
    if radius_m is not None:
        radius_m = min(max(radius_m, 1000), 500_000)
    sort = request.args.get("sort", "updated_desc") if include_sort else "updated_desc"
    return ListingSearch(
        q=request.args.get("q") or None,
        make=request.args.get("make") or None,
        model=request.args.get("model") or None,
        source=request.args.get("source") or None,
        route=request.args.get("route") or None,
        country=request.args.get("country") or None,
        import_us=request.args.get("import_us") in ("1", "true", "yes"),
        import_ca=request.args.get("import_ca") in ("1", "true", "yes"),
        year_min=request.args.get("year_min", type=int),
        year_max=request.args.get("year_max", type=int),
        price_min=request.args.get("price_min", type=float),
        price_max=request.args.get("price_max", type=float),
        lon=request.args.get("lon", type=float),
        lat=request.args.get("lat", type=float),
        radius_m=radius_m,
        sort=sort,
        limit=limit,
        offset=offset,
    )

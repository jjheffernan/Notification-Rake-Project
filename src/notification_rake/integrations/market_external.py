"""External market/sales volume data from public APIs (best-effort, optional keys)."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx

from notification_rake.config import settings

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, Any]] = {}
_USER_AGENT = settings.geocode_user_agent


@dataclass
class ExternalVolumeData:
    us_market_trend: list[dict[str, Any]] = field(default_factory=list)
    production: dict[str, Any] | None = None
    epa: dict[str, Any] | None = None
    nhtsa: dict[str, Any] | None = None
    brand_us_sales: dict[str, Any] | None = None
    model_regional_rank: dict[str, Any] | None = None
    sources_fetched: list[str] = field(default_factory=list)
    sources_skipped: list[dict[str, str]] = field(default_factory=list)


def _cache_get(key: str, ttl_sec: int) -> Any | None:
    entry = _CACHE.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.monotonic() - ts > ttl_sec:
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.monotonic(), value)


def _skip(result: ExternalVolumeData, source: str, reason: str) -> None:
    result.sources_skipped.append({"source": source, "reason": reason})


def _http_get(url: str, *, params: dict | None = None, headers: dict | None = None) -> Any:
    hdrs = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    with httpx.Client(timeout=12.0, headers=hdrs) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def fetch_fred_us_vehicle_sales(*, limit: int = 24) -> list[dict[str, Any]]:
    """US total vehicle sales (SAAR) from FRED TOTALSA — requires FRED_API_KEY."""
    api_key = settings.fred_api_key.strip()
    if not api_key:
        return []
    cache_key = f"fred:totalsa:{limit}"
    cached = _cache_get(cache_key, 86_400)
    if cached is not None:
        return cached
    data = _http_get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": "TOTALSA",
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
    )
    rows: list[dict[str, Any]] = []
    for obs in data.get("observations") or []:
        val = obs.get("value")
        if val in (None, ".", ""):
            continue
        try:
            rows.append(
                {
                    "month": obs.get("date"),
                    "sales_saar_millions": round(float(val), 3),
                    "units_label": "millions SAAR",
                }
            )
        except (TypeError, ValueError):
            continue
    rows.reverse()
    _cache_set(cache_key, rows)
    return rows


_PRODUCTION_PATTERNS = (
    re.compile(
        r"(?:total\s+)?production(?:\s+of|\s+was|\s+reached|\s+exceeded)?\s+"
        r"(?:about\s+|approximately\s+|over\s+|around\s+)?"
        r"([\d][\d,]*)\s*(?:units|vehicles|examples|copies|built)",
        re.I,
    ),
    re.compile(
        r"([\d][\d,]*)\s+(?:units|vehicles|examples)\s+(?:were\s+)?(?:built|produced|manufactured)",
        re.I,
    ),
    re.compile(r"([\d][\d,]*)\s+built\b", re.I),
)


def _parse_production_units(text: str) -> int | None:
    for pat in _PRODUCTION_PATTERNS:
        match = pat.search(text)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def fetch_wikipedia_production(make: str, model: str) -> dict[str, Any] | None:
    """Search Wikipedia for production / units-built figures."""
    cache_key = f"wiki:prod:{make}:{model}".lower()
    cached = _cache_get(cache_key, 604_800)
    if cached is not None:
        return cached

    search_q = f"{make} {model} automobile"
    search = _http_get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "opensearch",
            "search": search_q,
            "limit": 3,
            "namespace": 0,
            "format": "json",
        },
    )
    titles = search[1] if isinstance(search, list) and len(search) > 1 else []
    if not titles:
        _cache_set(cache_key, None)
        return None

    for title in titles:
        summary = _http_get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'))}"
        )
        extract = summary.get("extract") or ""
        units = _parse_production_units(extract)
        if units:
            result = {
                "units_produced": units,
                "source": "wikipedia",
                "title": title,
                "url": summary.get("content_urls", {}).get("desktop", {}).get("page"),
                "excerpt": extract[:280] + ("…" if len(extract) > 280 else ""),
            }
            _cache_set(cache_key, result)
            return result

    _cache_set(cache_key, None)
    return None


def fetch_epa_model_years(make: str, model: str) -> dict[str, Any] | None:
    """EPA FuelEconomy.gov — model years on file (proxy for US market presence)."""
    cache_key = f"epa:{make}:{model}".lower()
    cached = _cache_get(cache_key, 604_800)
    if cached is not None:
        return cached

    base = "https://fueleconomy.gov/ws/rest/vehicle"
    makes = _http_get(f"{base}/menu/make")
    make_match = next(
        (m for m in makes if str(m).lower() == make.strip().lower()),
        None,
    )
    if not make_match:
        _cache_set(cache_key, None)
        return None

    models = _http_get(f"{base}/menu/model", params={"make": make_match})
    model_norm = model.strip().lower()
    model_match = next(
        (m for m in models if str(m).lower() == model_norm or model_norm in str(m).lower()),
        None,
    )
    if not model_match:
        _cache_set(cache_key, None)
        return None

    years_raw = _http_get(f"{base}/menu/year", params={"make": make_match, "model": model_match})
    years = sorted(int(y) for y in years_raw if str(y).isdigit())

    if not years:
        _cache_set(cache_key, None)
        return None

    result = {
        "make": make_match,
        "model": model_match,
        "years_on_file": sorted(years),
        "year_count": len(years),
        "source": "epa_fueleconomy",
        "url": "https://www.fueleconomy.gov/",
    }
    _cache_set(cache_key, result)
    return result


def fetch_nhtsa_model_info(make: str, model: str) -> dict[str, Any] | None:
    """NHTSA vPIC — confirm make/model registration in US catalog."""
    cache_key = f"nhtsa:{make}:{model}".lower()
    cached = _cache_get(cache_key, 604_800)
    if cached is not None:
        return cached

    make_data = _http_get(
        f"https://vpic.nhtsa.dot.gov/api/vehicles/GetModelsForMake/{quote(make)}",
        params={"format": "json"},
    )
    results = make_data.get("Results") or []
    model_norm = model.strip().lower()
    matches = [
        r.get("Model_Name")
        for r in results
        if model_norm in str(r.get("Model_Name", "")).lower()
    ]
    if not matches:
        _cache_set(cache_key, None)
        return None

    result = {
        "make": make,
        "models_matched": sorted(set(str(m) for m in matches if m))[:12],
        "match_count": len(matches),
        "source": "nhtsa_vpic",
        "url": "https://vpic.nhtsa.dot.gov/api/",
    }
    _cache_set(cache_key, result)
    return result


def _cis_jwt() -> str | None:
    if settings.cis_automotive_jwt.strip():
        return settings.cis_automotive_jwt.strip()
    key = settings.cis_automotive_api_key.strip()
    secret = settings.cis_automotive_api_secret.strip()
    if not key or not secret:
        return None
    cache_key = "cis:jwt"
    cached = _cache_get(cache_key, 3500)
    if cached:
        return cached
    data = _http_get(
        f"{settings.cis_automotive_api_base.rstrip('/')}/getToken",
        params={"apiKey": key, "apiSecret": secret},
    )
    token = data.get("data") or data.get("jwt") or data.get("token")
    if isinstance(token, dict):
        token = token.get("jwt") or token.get("token")
    if not token:
        return None
    _cache_set(cache_key, str(token))
    return str(token)


def fetch_cis_brand_sales(make: str) -> dict[str, Any] | None:
    """CIS Automotive regionSales — US dealer sales by brand (optional JWT)."""
    jwt = _cis_jwt()
    if not jwt:
        return None

    region = settings.cis_automotive_region.strip() or "REGION_STATE_CA"
    month = settings.cis_automotive_sales_month.strip()
    if not month:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        month = f"{now.year}-{now.month:02d}-01"

    cache_key = f"cis:brand:{make}:{region}:{month}"
    cached = _cache_get(cache_key, 86_400)
    if cached is not None:
        return cached

    data = _http_get(
        f"{settings.cis_automotive_api_base.rstrip('/')}/regionSales",
        params={"jwt": jwt, "brandName": make, "regionName": region, "month": month},
    )
    payload = data.get("data")
    if not payload:
        _cache_set(cache_key, None)
        return None

    if isinstance(payload, list):
        total = sum(int(row.get("sales") or row.get("Sales") or 0) for row in payload)
        daily = payload
    elif isinstance(payload, dict):
        total = int(payload.get("sales") or payload.get("Sales") or 0)
        daily = payload.get("daily") or payload.get("days") or []
    else:
        _cache_set(cache_key, None)
        return None

    result = {
        "brand": make,
        "region": region,
        "month": month,
        "dealer_sales": total,
        "daily_breakdown": daily[:31] if isinstance(daily, list) else [],
        "source": "cis_automotive",
        "url": "https://autodealerdata.com/",
    }
    _cache_set(cache_key, result)
    return result


def fetch_cis_model_rank(model: str) -> dict[str, Any] | None:
    """CIS Automotive topModels — regional model sales rank (last ~45 days)."""
    jwt = _cis_jwt()
    if not jwt:
        return None

    region = settings.cis_automotive_region.strip() or "REGION_STATE_CA"
    cache_key = f"cis:top:{region}"
    cached = _cache_get(cache_key, 86_400)
    if cached is None:
        data = _http_get(
            f"{settings.cis_automotive_api_base.rstrip('/')}/topModels",
            params={"jwt": jwt, "regionName": region},
        )
        cached = data.get("data") or []
        _cache_set(cache_key, cached)

    model_norm = model.strip().lower()
    for row in cached:
        name = str(row.get("modelName") or row.get("model") or "").lower()
        if model_norm in name or name in model_norm:
            return {
                "model": row.get("modelName") or row.get("model"),
                "region": region,
                "percent_of_top_sales": row.get("percentOfTopSales"),
                "brand_market_share": row.get("brandMarketShare"),
                "rank": row.get("rank") or row.get("salesRank"),
                "source": "cis_automotive",
                "url": "https://autodealerdata.com/",
            }
    return None


def fetch_external_volume_data(make: str, model: str) -> dict[str, Any]:
    """Aggregate external sales/volume signals for a make/model."""
    result = ExternalVolumeData()

    try:
        trend = fetch_fred_us_vehicle_sales()
        if trend:
            result.us_market_trend = trend
            result.sources_fetched.append("fred")
        elif settings.fred_api_key.strip():
            _skip(result, "fred", "no observations returned")
        else:
            _skip(result, "fred", "FRED_API_KEY not configured")
    except Exception as exc:
        logger.debug("fred fetch failed: %s", exc)
        _skip(result, "fred", str(exc))

    try:
        prod = fetch_wikipedia_production(make, model)
        if prod:
            result.production = prod
            result.sources_fetched.append("wikipedia")
        else:
            _skip(result, "wikipedia", "no production figure found")
    except Exception as exc:
        logger.debug("wikipedia fetch failed: %s", exc)
        _skip(result, "wikipedia", str(exc))

    try:
        epa = fetch_epa_model_years(make, model)
        if epa:
            result.epa = epa
            result.sources_fetched.append("epa")
        else:
            _skip(result, "epa", "model not in EPA database")
    except Exception as exc:
        logger.debug("epa fetch failed: %s", exc)
        _skip(result, "epa", str(exc))

    try:
        nhtsa = fetch_nhtsa_model_info(make, model)
        if nhtsa:
            result.nhtsa = nhtsa
            result.sources_fetched.append("nhtsa")
        else:
            _skip(result, "nhtsa", "no NHTSA model match")
    except Exception as exc:
        logger.debug("nhtsa fetch failed: %s", exc)
        _skip(result, "nhtsa", str(exc))

    if _cis_jwt():
        try:
            brand_sales = fetch_cis_brand_sales(make)
            if brand_sales:
                result.brand_us_sales = brand_sales
                result.sources_fetched.append("cis_brand_sales")
            else:
                _skip(result, "cis_brand_sales", "no sales data for brand/region")
        except Exception as exc:
            logger.debug("cis brand sales failed: %s", exc)
            _skip(result, "cis_brand_sales", str(exc))

        try:
            rank = fetch_cis_model_rank(model)
            if rank:
                result.model_regional_rank = rank
                result.sources_fetched.append("cis_model_rank")
            else:
                _skip(result, "cis_model_rank", "model not in regional top sellers")
        except Exception as exc:
            logger.debug("cis model rank failed: %s", exc)
            _skip(result, "cis_model_rank", str(exc))
    else:
        _skip(result, "cis_automotive", "CIS JWT or API keys not configured")

    return {
        "us_market_trend": result.us_market_trend,
        "production": result.production,
        "epa": result.epa,
        "nhtsa": result.nhtsa,
        "brand_us_sales": result.brand_us_sales,
        "model_regional_rank": result.model_regional_rank,
        "sources_fetched": result.sources_fetched,
        "sources_skipped": result.sources_skipped,
    }

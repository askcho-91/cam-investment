"""
Company price-chart caching.

Strategy:
- Cold cache: fetch the full history your plan allows (`period=all`,
  `format=chart`) once per symbol and store it in Redis as a single
  [timestamp_ms, close] series, sorted ascending.
- Warm cache: on each call, only top up the days missing since the last
  cached point (`from=<last_date+1>&to=today`) instead of re-fetching
  the whole range.
- Any period/from/to the frontend asks for is served by slicing the
  cached full series locally — no extra API call for range changes.

Assumes `NGN_MARKET_API_URL`, `NGN_MARKET_API_KEY`, and `redis_dependency`
are already defined/imported the same way as in your existing indices
function.
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from os import getenv
from app.core.dependencies import redis_dependency

import httpx

logger = logging.getLogger(__name__)

NGN_MARKET_API_URL = getenv("NGN_MARKET_API_URL")
NGN_MARKET_API_KEY = getenv("NGN_MARKET_API_KEY")

CHART_CACHE_PREFIX = "chart"

# How long a warm cache is trusted before we check for a top-up. This isn't
# the freshness of the *data* (past days never change) — it's just how often
# we bother asking the API "is there anything new since my last point?".
CHART_CACHE_CHECK_TTL_SECONDS = 60 * 60 * 6  # 6 hours

VALID_PERIODS = {"7d", "30d", "90d", "1y", "5y", "all"}

_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365, "5y": 365 * 5}


def _cache_key(symbol: str) -> str:
    return f"{CHART_CACHE_PREFIX}:{symbol.upper()}"


def _checked_key(symbol: str) -> str:
    """Separate short-TTL key that just gates how often we check for a top-up."""
    return f"{CHART_CACHE_PREFIX}:checked:{symbol.upper()}"


def _last_cached_date(series: list) -> Optional[date]:
    if not series:
        return None
    last_ts_ms = series[-1][0]
    return datetime.fromtimestamp(last_ts_ms / 1000, tz=timezone.utc).date()


async def _fetch_chart(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    period: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> list:
    params = {"format": "chart"}
    if from_date:
        params["from"] = from_date
        if to_date:
            params["to"] = to_date
    elif period:
        params["period"] = period

    response = await client.get(
        f"{NGN_MARKET_API_URL}/companies/{symbol}/chart",
        params=params,
        headers={"Authorization": f"Bearer {NGN_MARKET_API_KEY}"},
    )

    if response.status_code == 404:
        return []  # no chart data at all for this symbol

    response.raise_for_status()
    return response.json().get("data", {}).get("data", [])


async def _load_full_history(symbol: str, redis: redis_dependency) -> list:
    """
    Returns the full cached [timestamp_ms, close] series for `symbol`,
    sorted ascending. Fetches everything on a cold cache; tops up
    incrementally on a warm-but-stale cache.
    """
    cache_key = _cache_key(symbol)
    checked_key = _checked_key(symbol)

    cached_raw = await redis.get(cache_key)
    series: list = json.loads(cached_raw) if cached_raw else []

    # Cold cache: nothing stored yet, pull the whole range the plan allows.
    if not series:
        async with httpx.AsyncClient() as client:
            series = await _fetch_chart(client, symbol, period="all")
        if series:
            await redis.set(cache_key, json.dumps(series))
            await redis.setex(checked_key, CHART_CACHE_CHECK_TTL_SECONDS, "1")
        return series

    # Warm cache, checked recently: trust it, skip hitting the API again.
    if await redis.get(checked_key):
        return series

    # Warm cache, due for a top-up check: only fetch what might be missing.
    last_date = _last_cached_date(series)
    today = datetime.now(timezone.utc).date()

    if last_date is not None and last_date < today:
        gap_start = (last_date + timedelta(days=1)).isoformat()
        gap_end = today.isoformat()

        async with httpx.AsyncClient() as client:
            new_points = await _fetch_chart(
                client, symbol, from_date=gap_start, to_date=gap_end
            )

        if new_points:
            existing_ts = {point[0] for point in series}
            series.extend(p for p in new_points if p[0] not in existing_ts)
            series.sort(key=lambda p: p[0])
            await redis.set(cache_key, json.dumps(series))

    await redis.setex(checked_key, CHART_CACHE_CHECK_TTL_SECONDS, "1")
    return series


def _slice_range(
    series: list,
    *,
    period: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> list:
    """Mirrors the API's own rule: from/to takes priority over period."""
    if not series:
        return []

    if from_date:
        start_ts = int(
            datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc).timestamp()
            * 1000
        )
        end_ts = (
            int(
                datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc).timestamp()
                * 1000
            )
            if to_date
            else series[-1][0]
        )
        return [p for p in series if start_ts <= p[0] <= end_ts]

    if period and period != "all":
        days = _PERIOD_DAYS.get(period)
        if days:
            cutoff_ts = int(
                (datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000
            )
            return [p for p in series if p[0] >= cutoff_ts]

    return series


def _compute_statistics(series: list) -> dict:
    closes = [p[1] for p in series if p[1] is not None]
    if not series or not closes:
        return {}

    first_price = series[0][1]
    last_price = series[-1][1]
    change = (
        last_price - first_price
        if first_price is not None and last_price is not None
        else None
    )

    return {
        "first_price": first_price,
        "last_price": last_price,
        "min_price": min(closes),
        "max_price": max(closes),
        "price_change": change,
        "price_change_percent": (
            round((change / first_price) * 100, 4)
            if change is not None and first_price
            else None
        ),
        "start_date": datetime.fromtimestamp(series[0][0] / 1000, tz=timezone.utc)
        .date()
        .isoformat(),
        "end_date": datetime.fromtimestamp(series[-1][0] / 1000, tz=timezone.utc)
        .date()
        .isoformat(),
    }


async def get_company_chart(
    symbol: str,
    redis: redis_dependency,
    *,
    period: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> dict:
    """
    Line-chart data for a company, backed by a Redis-cached full history.

    Call this the same way regardless of what range the frontend wants —
    pass through whatever `period` (7d/30d/90d/1y/5y/all) or `from`/`to`
    the request came in with. The full history is fetched/topped-up once
    per symbol; every range request after that is served from the cached
    series with no extra call to the upstream API.
    """
    symbol = symbol.upper()

    if period and period not in VALID_PERIODS:
        return {
            "error": f"Invalid period '{period}'. Must be one of {sorted(VALID_PERIODS)}."
        }

    try:
        full_series = await _load_full_history(symbol, redis)
    except httpx.HTTPStatusError as exc:
        return {
            "error": f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}"
        }

    if not full_series:
        return {"error": f"No chart data available for {symbol}."}

    sliced = _slice_range(
        full_series, period=period, from_date=from_date, to_date=to_date
    )

    return {
        "symbol": symbol,
        "format": "chart",
        "period": period or ("custom" if from_date else "all"),
        "count": len(sliced),
        "data": sliced,
        "statistics": _compute_statistics(sliced),
    }


async def get_company_profile(symbol: str, redis: redis_dependency):
    symbol = symbol.upper()

    result = await redis.get(f"COMPANY_PROFILE:{symbol}")
    if result:
        logger.info("FOUND!!!!")
        return json.loads(result)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NGN_MARKET_API_URL}/companies/{symbol}",
                headers={"Authorization": f"Bearer {NGN_MARKET_API_KEY}"},
            )
            response.raise_for_status()
            raw_data = response.json()

            data = raw_data.get("data")
            await redis.setex(f"COMPANY_PROFILE:{symbol}", 60 * 60, json.dumps(data))

            return data
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }

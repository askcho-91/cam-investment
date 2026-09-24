"""
Market chart caching (companies + indices), plus company profile caching.

Strategy (shared by both companies and indices charts):
- Cold cache: fetch the full history the plan allows (`period=all`,
  `format=chart`) once per symbol and store it in Redis as a single
  [timestamp_ms, value] series, sorted ascending.
- Warm cache: gated by a short-TTL "checked" key so we're not hitting the
  API on every request just to ask "anything new?". Once that expires,
  top up only the days missing since the last cached point instead of
  re-fetching the whole range.
- Any period/from/to the frontend asks for is served by slicing the
  cached full series locally — no extra API call for range changes.

Companies and indices differ only in URL segment, cache prefix, and the
shape of their statistics block (indices add return_1m/3m/1y/ytd computed
against fixed historical reference points, independent of the requested
period) — everything else is shared.

Forex (/forex/history) doesn't fit that shared path/period-based shape —
it's keyed by a source/target currency pair via query params, has no
`period` or `format=chart` option, and always returns flat
{date, currency, rate} objects (newest first) instead of [timestamp, value]
pairs. It gets its own fetch/cache functions below, but reuses the same
slicing logic and top-up strategy once normalized to [timestamp_ms, rate].
"""

import bisect
import json
import logging
from datetime import date, datetime, timedelta, timezone
from os import getenv
from typing import Literal, Optional

import httpx
from app.core.dependencies import redis_dependency

logger = logging.getLogger(__name__)

NGN_MARKET_API_URL = getenv("NGN_MARKET_API_URL")
NGN_MARKET_API_KEY = getenv("NGN_MARKET_API_KEY")

# How long a warm cache is trusted before we check for a top-up. This isn't
# the freshness of the *data* (past days never change) — it's just how often
# we bother asking the API "is there anything new since my last point?".
CHART_CACHE_CHECK_TTL_SECONDS = 60 * 60 * 6  # 6 hours

VALID_PERIODS = {"7d", "30d", "90d", "1y", "5y", "all"}
_PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365, "5y": 365 * 5}

ChartKind = Literal["companies", "indices"]

_CHART_CONFIG = {
    "companies": {"url_segment": "companies", "cache_prefix": "chart"},
    "indices": {"url_segment": "indices", "cache_prefix": "index_chart"},
}

# Forex has no `period=all` equivalent — to pull "everything the plan
# allows" on a cold cache we just ask from far enough back that the API
# clamps `from` to the earliest date we're entitled to (per the docs).
FOREX_EARLIEST_FROM = "2000-01-01"
FOREX_CACHE_PREFIX = "forex_chart"


# --------------------------------------------------------------------------
# Shared cache / fetch / slice logic
# --------------------------------------------------------------------------


def _cache_key(kind: ChartKind, symbol: str) -> str:
    return f"{_CHART_CONFIG[kind]['cache_prefix']}:{symbol.upper()}"


def _checked_key(kind: ChartKind, symbol: str) -> str:
    return f"{_CHART_CONFIG[kind]['cache_prefix']}:checked:{symbol.upper()}"


def _last_cached_date(series: list) -> Optional[date]:
    if not series:
        return None
    return datetime.fromtimestamp(series[-1][0] / 1000, tz=timezone.utc).date()


async def _fetch_chart(
    client: httpx.AsyncClient,
    kind: ChartKind,
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

    url_segment = _CHART_CONFIG[kind]["url_segment"]
    response = await client.get(
        f"{NGN_MARKET_API_URL}/{url_segment}/{symbol}/chart",
        params=params,
        headers={"Authorization": f"Bearer {NGN_MARKET_API_KEY}"},
    )

    if response.status_code == 404:
        return []  # unknown symbol / no chart data

    response.raise_for_status()
    return response.json().get("data", {}).get("data", [])


async def _load_full_history(
    kind: ChartKind, symbol: str, redis: redis_dependency
) -> list:
    """
    Returns the full cached [timestamp_ms, value] series for `symbol`,
    sorted ascending. Fetches everything on a cold cache; tops up
    incrementally on a warm-but-stale cache.
    """
    cache_key = _cache_key(kind, symbol)
    checked_key = _checked_key(kind, symbol)

    cached_raw = await redis.get(cache_key)
    series: list = json.loads(cached_raw) if cached_raw else []

    # Cold cache: nothing stored yet, pull the whole range the plan allows.
    if not series:
        async with httpx.AsyncClient() as client:
            series = await _fetch_chart(client, kind, symbol, period="all")
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
                client, kind, symbol, from_date=gap_start, to_date=gap_end
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


async def _get_chart(
    kind: ChartKind,
    symbol: str,
    redis: redis_dependency,
    *,
    period: Optional[str],
    from_date: Optional[str],
    to_date: Optional[str],
) -> dict:
    """Shared entry point behind get_company_chart / get_index_chart."""
    symbol = symbol.upper()

    if period and period not in VALID_PERIODS:
        return {
            "error": f"Invalid period '{period}'. Must be one of {sorted(VALID_PERIODS)}."
        }

    try:
        full_series = await _load_full_history(kind, symbol, redis)
    except httpx.HTTPStatusError as exc:
        return {
            "error": f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}"
        }

    if not full_series:
        noun = "company" if kind == "companies" else "index"
        return {"error": f"No chart data available for {noun} '{symbol}'."}

    sliced = _slice_range(
        full_series, period=period, from_date=from_date, to_date=to_date
    )
    statistics = (
        _compute_company_statistics(sliced)
        if kind == "companies"
        else _compute_index_statistics(full_series, sliced)
    )

    return {
        "symbol": symbol,
        "format": "chart",
        "period": period or ("custom" if from_date else "all"),
        "count": len(sliced),
        "data": sliced,
        "statistics": statistics,
    }


# --------------------------------------------------------------------------
# Company-specific statistics
# --------------------------------------------------------------------------


def _compute_company_statistics(series: list) -> dict:
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


# --------------------------------------------------------------------------
# Index-specific statistics (adds fixed-reference returns)
# --------------------------------------------------------------------------


def _value_at_or_before(series: list, target_ts_ms: int) -> Optional[float]:
    """Last point's value with timestamp <= target_ts_ms, in a series sorted ascending."""
    if not series:
        return None
    timestamps = [p[0] for p in series]
    idx = bisect.bisect_right(timestamps, target_ts_ms) - 1
    if idx < 0:
        return None
    return series[idx][1]


def _fixed_reference_returns(full_series: list) -> dict:
    """
    return_1m / return_3m / return_1y / return_ytd, matching the API's own
    semantics: computed off the most recent point in the full history,
    independent of whatever period/range was requested.
    """
    if not full_series:
        return {
            "return_1m": None,
            "return_3m": None,
            "return_1y": None,
            "return_ytd": None,
        }

    latest_ts, latest_value = full_series[-1]
    latest_dt = datetime.fromtimestamp(latest_ts / 1000, tz=timezone.utc)

    def pct_return(
        days_back: Optional[int] = None, ytd: bool = False
    ) -> Optional[float]:
        if latest_value is None:
            return None
        ref_dt = (
            datetime(latest_dt.year, 1, 1, tzinfo=timezone.utc)
            if ytd
            else latest_dt - timedelta(days=days_back)
        )
        ref_value = _value_at_or_before(full_series, int(ref_dt.timestamp() * 1000))
        if ref_value is None or ref_value == 0:
            return None
        return round((latest_value - ref_value) / ref_value * 100, 4)

    return {
        "return_1m": pct_return(days_back=30),
        "return_3m": pct_return(days_back=90),
        "return_1y": pct_return(days_back=365),
        "return_ytd": pct_return(ytd=True),
    }


def _compute_index_statistics(full_series: list, sliced: list) -> dict:
    closes = [p[1] for p in sliced if p[1] is not None]
    if not sliced or not closes:
        return {}

    start_value = sliced[0][1]
    end_value = sliced[-1][1]
    change = (
        end_value - start_value
        if start_value is not None and end_value is not None
        else None
    )

    stats = {
        "start_date": datetime.fromtimestamp(sliced[0][0] / 1000, tz=timezone.utc)
        .date()
        .isoformat(),
        "end_date": datetime.fromtimestamp(sliced[-1][0] / 1000, tz=timezone.utc)
        .date()
        .isoformat(),
        "start_value": start_value,
        "end_value": end_value,
        "change": change,
        "change_percent": (
            round(change / start_value * 100, 4)
            if change is not None and start_value
            else None
        ),
        "min_value": min(closes),
        "max_value": max(closes),
    }
    stats.update(_fixed_reference_returns(full_series))
    return stats


# --------------------------------------------------------------------------
# Forex-specific fetch / cache / statistics
# --------------------------------------------------------------------------


def _forex_cache_key(source: str, target: str) -> str:
    return f"{FOREX_CACHE_PREFIX}:{source.upper()}_{target.upper()}"


def _forex_checked_key(source: str, target: str) -> str:
    return f"{FOREX_CACHE_PREFIX}:checked:{source.upper()}_{target.upper()}"


async def _fetch_forex(
    client: httpx.AsyncClient,
    source: str,
    target: str,
    *,
    from_date: str,
    to_date: Optional[str] = None,
) -> list:
    """
    Fetches raw {date, currency, rate} rows and normalizes them into
    [timestamp_ms, rate] pairs sorted ascending (the API returns newest
    first).
    """
    params = {"source": source, "target": target, "from": from_date}
    if to_date:
        params["to"] = to_date

    response = await client.get(
        f"{NGN_MARKET_API_URL}/forex/history",
        params=params,
        headers={"Authorization": f"Bearer {NGN_MARKET_API_KEY}"},
    )
    response.raise_for_status()  # 400 invalid currency raises here

    payload = response.json()
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    if isinstance(rows, dict):
        rows = rows.get("data", [])

    series = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict):
            raw_date = row.get("rate_date") or row.get("date") or row.get("timestamp")
            raw_rate = row.get("rate") or row.get("exchange_rate")
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            raw_date, raw_rate = row[0], row[1]
        else:
            continue
        if raw_date is None or raw_rate is None:
            continue
        try:
            parsed_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            series.append([int(parsed_date.timestamp() * 1000), float(raw_rate)])
        except TypeError, ValueError:
            continue
    series.sort(key=lambda p: p[0])
    return series


async def _load_full_forex_history(
    source: str, target: str, redis: redis_dependency
) -> list:
    cache_key = _forex_cache_key(source, target)
    checked_key = _forex_checked_key(source, target)

    cached_raw = await redis.get(cache_key)
    series: list = json.loads(cached_raw) if cached_raw else []

    # Cold cache: pull everything the plan allows.
    if not series:
        async with httpx.AsyncClient() as client:
            series = await _fetch_forex(
                client, source, target, from_date=FOREX_EARLIEST_FROM
            )
        if series:
            await redis.set(cache_key, json.dumps(series))
            await redis.setex(checked_key, CHART_CACHE_CHECK_TTL_SECONDS, "1")
        return series

    # Warm cache, checked recently: trust it.
    if await redis.get(checked_key):
        return series

    # Warm cache, due for a top-up check.
    last_date = _last_cached_date(series)
    today = datetime.now(timezone.utc).date()

    if last_date is not None and last_date < today:
        gap_start = (last_date + timedelta(days=1)).isoformat()
        gap_end = today.isoformat()

        async with httpx.AsyncClient() as client:
            new_points = await _fetch_forex(
                client, source, target, from_date=gap_start, to_date=gap_end
            )

        if new_points:
            existing_ts = {point[0] for point in series}
            series.extend(p for p in new_points if p[0] not in existing_ts)
            series.sort(key=lambda p: p[0])
            await redis.set(cache_key, json.dumps(series))

    await redis.setex(checked_key, CHART_CACHE_CHECK_TTL_SECONDS, "1")
    return series


def _compute_forex_statistics(series: list) -> dict:
    rates = [p[1] for p in series if p[1] is not None]
    if not series or not rates:
        return {}

    first_rate = series[0][1]
    last_rate = series[-1][1]
    change = (
        last_rate - first_rate
        if first_rate is not None and last_rate is not None
        else None
    )

    return {
        "first_rate": first_rate,
        "last_rate": last_rate,
        "min_rate": min(rates),
        "max_rate": max(rates),
        "rate_change": change,
        "rate_change_percent": (
            round((change / first_rate) * 100, 4)
            if change is not None and first_rate
            else None
        ),
        "start_date": datetime.fromtimestamp(series[0][0] / 1000, tz=timezone.utc)
        .date()
        .isoformat(),
        "end_date": datetime.fromtimestamp(series[-1][0] / 1000, tz=timezone.utc)
        .date()
        .isoformat(),
    }


# --------------------------------------------------------------------------
# Public functions
# --------------------------------------------------------------------------


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
    the request came in with.
    """
    return await _get_chart(
        "companies", symbol, redis, period=period, from_date=from_date, to_date=to_date
    )


async def get_index_chart(
    symbol: str,
    redis: redis_dependency,
    *,
    period: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> dict:
    """
    Line-chart data for an NGX index, backed by a Redis-cached full history.
    Same call shape as get_company_chart.
    """
    return await _get_chart(
        "indices", symbol, redis, period=period, from_date=from_date, to_date=to_date
    )


async def get_forex_chart(
    source: str,
    target: str,
    redis: redis_dependency,
    *,
    period: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> dict:
    """
    Line-chart data for a Forex currency pair, backed by a Redis-cached
    full history.

    The currency pair is identified by source/target currencies.
    The full history is cached and the requested period or custom
    from/to range is sliced locally.
    """
    source = source.upper()
    target = target.upper()

    if period and period not in VALID_PERIODS:
        return {
            "error": (
                f"Invalid period '{period}'. "
                f"Must be one of {sorted(VALID_PERIODS)}."
            )
        }

    if source == target:
        return {"error": "Source and target currencies must be different."}

    try:
        full_series = await _load_full_forex_history(
            source,
            target,
            redis,
        )
    except httpx.HTTPStatusError as exc:
        return {
            "error": (
                f"HTTP error occurred: "
                f"{exc.response.status_code} - {exc.response.text}"
            )
        }

    if not full_series:
        return {"error": (f"No Forex data available for " f"{source}/{target}.")}

    sliced = _slice_range(
        full_series,
        period=period,
        from_date=from_date,
        to_date=to_date,
    )

    statistics = _compute_forex_statistics(sliced)

    return {
        "source": source,
        "target": target,
        "pair": f"{source}/{target}",
        "format": "chart",
        "period": period or ("custom" if from_date else "all"),
        "count": len(sliced),
        "data": sliced,
        "statistics": statistics,
    }


# --------------------------------------------------------------------------
# Company profile (unchanged from existing implementation)
# --------------------------------------------------------------------------


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

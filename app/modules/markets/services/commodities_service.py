from logging import getLogger

from app.core.dependencies import redis_dependency
from app.modules.markets.constants import COMMODITIES_CACHE_TTL, DEFAULT_COMMODITIES
from app.modules.markets.services.av_client import cached_av_get, to_float

logger = getLogger(__name__)


async def get_commodity(
    redis: redis_dependency, function: str, interval: str = "monthly"
) -> dict:
    cache_key = f"commodity:{function}:{interval}"
    params = {"function": function, "interval": interval}
    raw_data = await cached_av_get(redis, cache_key, params, COMMODITIES_CACHE_TTL)

    if "error" in raw_data:
        return {"commodity": function, "ticker": function, **raw_data}

    # AV's commodity endpoints return a time series ordered newest-first;
    # take the two most recent points so callers (e.g. the frontend) get a
    # ready-to-use percent_change instead of just a single price.
    data_points = raw_data.get("data", [])
    latest = data_points[0] if data_points else {}
    previous = data_points[1] if len(data_points) > 1 else {}

    latest_value = to_float(latest.get("value"))
    previous_value = to_float(previous.get("value"))
    percent_change = None
    if latest_value is not None and previous_value:
        percent_change = round(((latest_value - previous_value) / previous_value) * 100, 2)

    return {
        "commodity": raw_data.get("name", function),
        "ticker": function,
        "unit": raw_data.get("unit"),
        "interval": raw_data.get("interval", interval),
        "latest_date": latest.get("date"),
        "latest_value": latest_value,
        "previous_value": previous_value,
        "percent_change": percent_change,
    }


async def get_commodities(
    redis: redis_dependency,
    functions: list[str] | None = None,
    interval: str = "monthly",
) -> list[dict]:
    """NOTE: one Alpha Vantage call per commodity - there's no batch endpoint."""
    functions = functions or DEFAULT_COMMODITIES
    results = []
    for function in functions:
        results.append(await get_commodity(redis, function, interval))
    return results

from logging import getLogger

from app.core.dependencies import redis_dependency
from app.modules.markets.constants import DEFAULT_MUTUAL_FUNDS, MUTUAL_FUND_CACHE_TTL
from app.modules.markets.services.av_client import cached_av_get, to_float

logger = getLogger(__name__)


async def get_mutual_fund(redis: redis_dependency, symbol: str) -> dict:
    # Mutual funds only reprice once a day (NAV), so TIME_SERIES_DAILY's
    # most recent entry is effectively the "current" price.
    cache_key = f"mutual_fund:{symbol}"
    params = {"function": "TIME_SERIES_DAILY", "symbol": symbol}
    raw_data = await cached_av_get(redis, cache_key, params, MUTUAL_FUND_CACHE_TTL)

    if "error" in raw_data:
        return {"symbol": symbol, **raw_data}

    series = raw_data.get("Time Series (Daily)", {})
    if not series:
        return {"symbol": symbol, "error": "No data returned for this symbol"}

    dates = list(series.keys())
    latest_date = dates[0]
    latest = series[latest_date]
    previous_date = dates[1] if len(dates) > 1 else None
    previous = series[previous_date] if previous_date else {}

    latest_nav = to_float(latest.get("4. close"))
    previous_nav = to_float(previous.get("4. close")) if previous else None
    percent_change = None
    if latest_nav is not None and previous_nav:
        percent_change = round(((latest_nav - previous_nav) / previous_nav) * 100, 2)

    return {
        "symbol": symbol,
        "nav_date": latest_date,
        "nav": latest_nav,
        "previous_nav": previous_nav,
        "percent_change": percent_change,
        "currency": "USD",
    }


async def get_mutual_funds(
    redis: redis_dependency, symbols: list[str] | None = None
) -> list[dict]:
    """NOTE: one Alpha Vantage call per fund - there's no batch endpoint."""
    symbols = symbols or DEFAULT_MUTUAL_FUNDS
    results = []
    for symbol in symbols:
        results.append(await get_mutual_fund(redis, symbol))
    return results

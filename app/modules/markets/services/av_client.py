import json
from datetime import datetime, timedelta, timezone
from logging import getLogger
from os import getenv

import httpx

from app.core.dependencies import redis_dependency

logger = getLogger(__name__)

ALPHA_VANTAGE_API_URL = getenv("ALPHA_VANTAGE_API_URL")
ALPHA_VANTAGE_API_KEY = getenv("ALPHA_VANTAGE_API_KEY")

# Alpha Vantage's free tier is brutally limited (25 requests/day, 5/min as
# of late 2024/2025). That budget is SHARED across every Alpha-Vantage
# backed endpoint in the app - forex, commodities, mutual funds, indices,
# AND stocks.get_global_movers() in the existing stocks module. One noisy
# endpoint could otherwise silently burn the whole day's quota for
# everyone else, so we track usage in Redis and refuse new calls once the
# budget's spent rather than let AV's API return a throttled response.
ALPHA_VANTAGE_DAILY_LIMIT = int(getenv("ALPHA_VANTAGE_DAILY_LIMIT", "25"))
AV_BUDGET_KEY = "av:daily_call_count"


class AlphaVantageBudgetExceeded(Exception):
    """Raised when the shared Alpha Vantage daily call budget is exhausted."""


def to_float(value) -> float | None:
    """Alpha Vantage returns numbers as strings (or omits them); coerce
    safely instead of letting a bad/missing value blow up a response."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _seconds_until_midnight_utc() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((tomorrow - now).total_seconds())


async def _reserve_av_call(redis: redis_dependency) -> None:
    """Increment the shared daily counter; raise once the budget's spent."""
    count = await redis.incr(AV_BUDGET_KEY)
    if count == 1:
        # first call of the day - set the counter to expire at UTC midnight
        await redis.expire(AV_BUDGET_KEY, _seconds_until_midnight_utc())
    if count > ALPHA_VANTAGE_DAILY_LIMIT:
        raise AlphaVantageBudgetExceeded(
            f"Alpha Vantage daily call budget ({ALPHA_VANTAGE_DAILY_LIMIT}) exhausted for today."
        )


async def cached_av_get(
    redis: redis_dependency,
    cache_key: str,
    params: dict,
    ttl_seconds: int,
) -> dict:
    """
    Fetch from Alpha Vantage with Redis caching plus a shared daily-budget
    guard. Always checks the cache first - a cache hit costs nothing
    against the budget, which is the whole point of caching this
    aggressively for a 25-req/day provider.
    """
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    try:
        await _reserve_av_call(redis)
    except AlphaVantageBudgetExceeded as e:
        logger.warning(str(e))
        return {"error": str(e)}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{ALPHA_VANTAGE_API_URL}/query",
                params={**params, "apikey": ALPHA_VANTAGE_API_KEY},
            )
            response.raise_for_status()
            raw_data = response.json()

            # Alpha Vantage returns HTTP 200 with a polite message body when
            # you're rate-limited or hand it a bad param, instead of a
            # proper error status - so check for those keys explicitly.
            if "Note" in raw_data or "Information" in raw_data:
                message = raw_data.get("Note") or raw_data.get("Information")
                logger.warning(f"Alpha Vantage throttle/error message: {message}")
                return {"error": message}

            await redis.setex(cache_key, ttl_seconds, json.dumps(raw_data))
            return raw_data
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}

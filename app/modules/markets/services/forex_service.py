from logging import getLogger

from app.core.dependencies import redis_dependency
from app.modules.markets.constants import DEFAULT_FOREX_PAIRS, FOREX_CACHE_TTL
from app.modules.markets.services.av_client import cached_av_get

logger = getLogger(__name__)


async def get_forex_rate(redis: redis_dependency, from_currency: str, to_currency: str) -> dict:
    cache_key = f"forex:{from_currency}_{to_currency}"
    params = {
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": from_currency,
        "to_currency": to_currency,
    }
    raw_data = await cached_av_get(redis, cache_key, params, FOREX_CACHE_TTL)

    if "error" in raw_data:
        return {"pair": f"{from_currency}/{to_currency}", **raw_data}

    quote = raw_data.get("Realtime Currency Exchange Rate", {})
    return {
        "pair": f"{from_currency}/{to_currency}",
        "exchange_rate": quote.get("5. Exchange Rate"),
        "last_refreshed": quote.get("6. Last Refreshed"),
        "bid_price": quote.get("8. Bid Price"),
        "ask_price": quote.get("9. Ask Price"),
    }


async def get_forex_rates(
    redis: redis_dependency, pairs: list[tuple[str, str]] | None = None
) -> list[dict]:
    """
    Fetch a batch of forex pairs. Defaults to DEFAULT_FOREX_PAIRS.

    NOTE: Alpha Vantage has no batch FX endpoint - N pairs means N calls
    against the shared daily budget, so keep custom `pairs` lists short.
    """
    pairs = pairs or DEFAULT_FOREX_PAIRS
    results = []
    for from_currency, to_currency in pairs:
        results.append(await get_forex_rate(redis, from_currency, to_currency))
    return results

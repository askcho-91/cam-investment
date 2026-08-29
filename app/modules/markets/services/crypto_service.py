import json
from logging import getLogger
from os import getenv

import httpx

from app.core.dependencies import redis_dependency
from app.modules.markets.constants import CRYPTO_CACHE_TTL, DEFAULT_CRYPTO_IDS

logger = getLogger(__name__)

# CoinGecko's public API needs no key on the free tier and has a far more
# generous rate limit than Alpha Vantage, so crypto gets its own provider
# rather than competing for AV's 25-req/day budget. COINGECKO_API_KEY is
# optional - only set it if you're on a paid CoinGecko plan.
COINGECKO_API_URL = getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")
COINGECKO_API_KEY = getenv("COINGECKO_API_KEY")


async def get_crypto_prices(
    redis: redis_dependency,
    coin_ids: list[str] | None = None,
    vs_currency: str = "usd",
) -> list[dict] | dict:
    coin_ids = coin_ids or DEFAULT_CRYPTO_IDS
    cache_key = f"crypto:{vs_currency}:{','.join(sorted(coin_ids))}"

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{COINGECKO_API_URL}/simple/price",
                params={
                    "ids": ",".join(coin_ids),
                    "vs_currencies": vs_currency,
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                },
                headers=headers,
            )
            response.raise_for_status()
            raw_data = response.json()

            result = [
                {
                    "id": coin_id,
                    "price": data.get(vs_currency),
                    "percent_change_24h": data.get(f"{vs_currency}_24h_change"),
                    "market_cap": data.get(f"{vs_currency}_market_cap"),
                    "currency": vs_currency.upper(),
                }
                for coin_id, data in raw_data.items()
            ]

            await redis.setex(cache_key, CRYPTO_CACHE_TTL, json.dumps(result))
            return result
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}

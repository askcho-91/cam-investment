from logging import getLogger
from os import getenv
from typing import Literal

import httpx

logger = getLogger(__name__)

FINNHUB_API_URL = getenv("FINNHUB_API_URL")
FINNHUB_API_KEY = getenv("FINNHUB_API_KEY")
COINGECKO_API_URL = getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")

# NOTE: NG-listed stocks are NOT searchable here. They come from
# NG_STOCK_API_URL (a different provider entirely, see stock_services.
# get_ng_stock_data), which doesn't expose a search endpoint. NG stock
# search stays a client-side filter over the already-fetched NG list.


async def search_finnhub(query: str) -> list[dict]:
    """
    Search stocks + ETFs via Finnhub's /search - one endpoint covers both;
    the `type` field on each result distinguishes them (e.g. "Common Stock"
    vs "ETP"). Deliberately uncached: search queries are too varied for a
    cache to help, and Finnhub's free-tier limit (60/min) comfortably
    covers ad-hoc typing without needing an Alpha-Vantage-style budget guard.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FINNHUB_API_URL}/search",
                params={"q": query, "token": FINNHUB_API_KEY},
            )
            response.raise_for_status()
            raw_data = response.json()
            return [
                {
                    "ticker": item.get("symbol"),
                    "name": item.get("description"),
                    "type": item.get("type"),
                    "market": "Global",
                }
                for item in raw_data.get("result", [])
                if item.get("symbol") and item.get("description")
            ]
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"Finnhub search HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return []
        except httpx.RequestError as e:
            logger.warning(f"Finnhub search request error: {str(e)}")
            return []


async def search_coingecko(query: str) -> list[dict]:
    """Search crypto via CoinGecko's /search - same reasoning as above, left uncached."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{COINGECKO_API_URL}/search", params={"query": query}
            )
            response.raise_for_status()
            raw_data = response.json()
            return [
                {
                    "id": coin.get("id"),
                    "name": coin.get("name"),
                    "symbol": coin.get("symbol"),
                    "asset_type": "crypto",
                }
                for coin in raw_data.get("coins", [])
            ]
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"CoinGecko search HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return []
        except httpx.RequestError as e:
            logger.warning(f"CoinGecko search request error: {str(e)}")
            return []


async def search(
    query: str, asset_type: Literal["stock", "etf", "crypto"]
) -> list[dict]:
    query = query.strip()
    if not query:
        return []
    if asset_type == "crypto":
        return await search_coingecko(query)
    results = await search_finnhub(query)
    if asset_type == "etf":
        return [
            item
            for item in results
            if str(item.get("type", "")).upper() in {"ETP", "ETF"}
        ]
    return [
        item
        for item in results
        if str(item.get("type", "")).upper() not in {"ETP", "ETF"}
    ]

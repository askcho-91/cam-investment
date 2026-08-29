import asyncio
from os import getenv
import httpx
from app.core.dependencies import redis_dependency
import json
from logging import getLogger
from dotenv import load_dotenv
from datetime import datetime
import pytz

# load_dotenv()

logging = getLogger(__name__)

# Market timezones
LAGOS_TZ = pytz.timezone("Africa/Lagos")
ET_TZ = pytz.timezone("US/Eastern")

# Market hours (weekdays only)
NGX_OPEN = 9  # 9:00 AM Lagos time
NGX_CLOSE = 14.5  # 2:30 PM Lagos time
US_OPEN = 9.5  # 9:30 AM ET
US_CLOSE = 16  # 4:00 PM ET


def get_market_ttl(market_type="us"):
    """
    Calculate Redis TTL based on market hours.
    During market hours: short TTL (30s for frequent updates)
    During off-hours: long TTL (4 hours since data won't change)
    """
    now = datetime.now()
    is_weekday = now.weekday() < 5  # Monday=0, Friday=4

    if market_type == "ngx":
        local_time = now.astimezone(LAGOS_TZ)
        market_hour = local_time.hour + local_time.minute / 60
        is_open = is_weekday and NGX_OPEN <= market_hour < NGX_CLOSE
        return 30 if is_open else 14400  # 30s during hours, 4 hours off-hours
    else:  # US markets
        local_time = now.astimezone(ET_TZ)
        market_hour = local_time.hour + local_time.minute / 60
        is_open = is_weekday and US_OPEN <= market_hour < US_CLOSE
        return 30 if is_open else 14400  # 30s during hours, 4 hours off-hours


NG_STOCK_API_URL = getenv("NG_STOCK_API_URL")
FINNHUB_API_URL = getenv("FINNHUB_API_URL")
FINNHUB_API_KEY = getenv("FINNHUB_API_KEY")

NGN_MARKET_API_URL = getenv("NGN_MARKET_API_URL")
NGN_MARKET_API_KEY = getenv("NGN_MARKET_API_KEY")

ALPHA_VANTAGE_API_URL = getenv("ALPHA_VANTAGE_API_URL")
ALPHA_VANTAGE_API_key = getenv("ALPHA_VANTAGE_API_KEY")


async def get_ng_stock_data(redis: redis_dependency):
    result = await redis.get("ng_stock_data")
    if result:
        return json.loads(result)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(NG_STOCK_API_URL)
            response.raise_for_status()
            raw_data = response.json()
            result = {}
            for stock in raw_data:
                formatted_data = {
                    "symbol": stock.get("SYMBOL"),
                    "current_price": stock.get("Value"),
                    "percent_change": stock.get("PercChange"),
                    "currency": "NGN",
                }
                ticker_type = stock.get("TickerType")
                # group stocks by ticker type
                if ticker_type not in result:
                    result[ticker_type] = []
                result[ticker_type].append(formatted_data)
            await redis.setex(
                "ng_stock_data", get_market_ttl("ngx"), json.dumps(result)
            )
            logging.info(f"Caching data for: {result.keys()}")
            return result
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}


async def get_ng_indices(redis: redis_dependency):
    result = await redis.get("ng_indices")
    if result:
        return json.loads(result)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{NGN_MARKET_API_URL}/indices",
            headers={"Authorization": f"Bearer {NGN_MARKET_API_KEY}"},
        )
        response.raise_for_status()
        raw_data = response.json().get("data", {}).get("data", [])
        await redis.setex("ng_indices", get_market_ttl("ngx"), json.dumps(raw_data))
        return raw_data


async def get_multiple_finnhub_stock_data(
    redis: redis_dependency, symbols: list[str]
) -> list[dict]:
    async with httpx.AsyncClient() as client:
        # Create tasks while keeping track of which symbol belongs to which request
        try:
            tasks = []
            results = []
            for symbol in symbols:
                result = await redis.get(f"finnhub_stock_data:{symbol}")
                if result:
                    results.append(json.loads(result))
                    continue  # Skip if data is already cached
                task = client.get(
                    f"{FINNHUB_API_URL}/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            for symbol, response in zip(symbols, responses):
                result = await redis.get(f"finnhub_stock_data:{symbol}")
                response.raise_for_status()
                raw_data = response.json()
                formatted_data = {
                    "symbol": symbol,
                    "current_price": raw_data.get("c"),
                    "change": raw_data.get("d"),
                    "percent_change": raw_data.get("dp"),
                    "high_price": raw_data.get("h"),
                    "low_price": raw_data.get("l"),
                    "open_price": raw_data.get("o"),
                    "previous_close": raw_data.get("pc"),
                    "timestamp": raw_data.get("t"),
                }
                results.append(formatted_data)
                # Cache the result in Redis for 30 seconds

                await redis.setex(
                    f"finnhub_stock_data:{symbol}",
                    get_market_ttl("us"),
                    json.dumps(formatted_data),
                )

            return results
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}


async def get_ngn_movers(redis: redis_dependency):

    result = await redis.get("ngx_movers")
    if result:
        return json.loads(result)

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {NGN_MARKET_API_KEY}"}
        query_params = {"limit": 10}

        logging.info(f"Fetching NGX movers data from API...{headers} {query_params}")

        response = await client.get(f"{NGN_MARKET_API_URL}/blog/posts", headers=headers)
        response.raise_for_status()
        raw_data = response.json()

        await redis.setex("ngx_movers", get_market_ttl("ngx"), json.dumps(raw_data))
        return raw_data


async def get_global_movers(redis: redis_dependency):
    result = await redis.get("global_movers")
    if result:
        return json.loads(result)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{ALPHA_VANTAGE_API_URL}/query",
                params={
                    "function": "TOP_GAINERS_LOSERS",
                    "apikey": ALPHA_VANTAGE_API_key,
                },
            )
            response.raise_for_status()
            raw_data = response.json()

            await redis.setex(
                "global_movers", get_market_ttl("us"), json.dumps(raw_data)
            )
            return raw_data
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}

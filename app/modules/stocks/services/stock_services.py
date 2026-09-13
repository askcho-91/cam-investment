import asyncio
from os import getenv
import httpx
from app.core.dependencies import redis_dependency
import json
from logging import getLogger
from dotenv import load_dotenv
from datetime import datetime, timedelta
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
    # now = datetime.now()
    # is_weekday = now.weekday() < 5  # Monday=0, Friday=4

    # if market_type == "ngx":
    #     local_time = now.astimezone(LAGOS_TZ)
    #     market_hour = local_time.hour + local_time.minute / 60
    #     is_open = is_weekday and NGX_OPEN <= market_hour < NGX_CLOSE
    #     return 30 if is_open else 14400  # 30s during hours, 4 hours off-hours
    # else:  # US markets
    #     local_time = now.astimezone(ET_TZ)
    #     market_hour = local_time.hour + local_time.minute / 60
    #     is_open = is_weekday and US_OPEN <= market_hour < US_CLOSE
    #     return 30 if is_open else 14400  # 30s during hours, 4 hours off-hours
    return 6000


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
        if response.status_code != 200:
            return {
                "error": f"HTTP error occurred: {response.status_code} - {response.text}"
            }
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


async def get_stock_data_by_symbol(symbol: str, redis: redis_dependency) -> dict:
    symbol = symbol.strip().upper()
    if not symbol:
        return {"error": "Symbol is required"}
    result = await redis.get(f"finnhub_stock_data:{symbol}")
    if result:
        return json.loads(result)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FINNHUB_API_URL}/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
            )
            response.raise_for_status()
            raw_data = response.json()
            if not raw_data.get("c"):
                return {"error": "Stock quote not found"}
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
            await redis.setex(
                f"finnhub_stock_data:{symbol}",
                get_market_ttl("us"),
                json.dumps(formatted_data),
            )
            return formatted_data
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}


async def get_global_company_news(symbol: str, redis: redis_dependency) -> list[dict]:
    symbol = symbol.strip().upper()
    result = await redis.get(f"finnhub_company_news:{symbol}")
    if result:
        return json.loads(result)

    async with httpx.AsyncClient() as client:
        try:
            today = datetime.now().date()
            start = today - timedelta(days=30)
            response = await client.get(
                f"{FINNHUB_API_URL}/company-news",
                params={
                    "symbol": symbol,
                    "from": start.isoformat(),
                    "to": today.isoformat(),
                    "token": FINNHUB_API_KEY,
                },
            )
            response.raise_for_status()
            raw_data = response.json()
            normalized = [
                {
                    "id": item.get("id") or item.get("datetime"),
                    "headline": item.get("headline"),
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "summary": item.get("summary"),
                    "image": item.get("image"),
                    "datetime": item.get("datetime"),
                }
                for item in raw_data
                if item.get("headline") and item.get("url")
            ]
            await redis.setex(
                f"finnhub_company_news:{symbol}",
                60 * 60 * 24,  # Cache for 24 hours
                json.dumps(normalized),
            )
            return normalized
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}


async def get_ngn_movers(redis: redis_dependency):

    stocks = await get_ng_stock_data(redis=redis)

    sorted_by_change = sorted(
        stocks.get("EQUITIES", []),
        key=lambda x: x.get("percent_change", 0),
        reverse=True,
    )

    formated_top_movers = {
        "top_gainers": sorted_by_change[:10],
        "top_losers": sorted_by_change[-10:],
    }
    logging.info("Computed NGX movers: %s", len(formated_top_movers["top_gainers"]))

    return formated_top_movers


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

            if response.status_code != 200:
                return {
                    "error": f"HTTP error occurred: {response.status_code} - {response.text}"
                }

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

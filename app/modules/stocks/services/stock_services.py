import asyncio
from os import getenv
import httpx
from app.core.dependencies import redis_dependency
import json

NG_STOCK_API_URL = getenv("NG_STOCK_API_URL")
FINNHUB_API_URL = getenv("FINNHUB_API_URL")
FINNHUB_API_KEY = getenv("FINNHUB_API_KEY")

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
                }
                ticker_type = stock.get("TickerType")
                # group stocks by ticker type
                if ticker_type not in result:
                    result[ticker_type] = []
                result[ticker_type].append(formatted_data)
            await redis.setex("ng_stock_data", 30, json.dumps(result))
            return result
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"}
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}



async def get_multiple_finnhub_stock_data(redis: redis_dependency, symbols: list[str]) -> list[dict]:
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
                task = client.get(f"{FINNHUB_API_URL}/quote?symbol={symbol}&token={FINNHUB_API_KEY}")
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
                await redis.setex(f"finnhub_stock_data:{symbol}", 30, json.dumps(formatted_data))
                
            return results
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"}
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}
        
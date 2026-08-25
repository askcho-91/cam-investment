import asyncio
import enum
from os import getenv
import httpx
from app.core.dependencies import redis_dependency
import json

NG_STOCK_API_URL = getenv("NG_STOCK_API_URL")
FINNHUB_API_URL = getenv("FINNHUB_API_URL")
FINNHUB_API_KEY = getenv("FINNHUB_API_KEY")

class CategoryEnum(str, enum.Enum):
    merger = "merger"
    general = "general"
    forex = "forex"
    crypto = "crypto"

async def get_ng_stock_data(redis: redis_dependency):
    pass



async def get_global_news(redis: redis_dependency, category: CategoryEnum) -> list[dict]:
    async with httpx.AsyncClient() as client:
        try:
            result = await redis.get(f"finnhub_news_data:{category.value}")
            if result:
                return json.loads(result)
            
            response = await client.get(f"{FINNHUB_API_URL}/news?category={category.value}&token={FINNHUB_API_KEY}")
            response.raise_for_status()
            raw_data = response.json()
            print(f"Fetched {len(raw_data)} news articles for category '{category.value}' from Finnhub API.")
            formatted_data = []
            for news in raw_data:
                formatted_news = {
                    "headline": news.get("headline"),
                    "source": news.get("source"),
                    "url": news.get("url"),
                    "summary": news.get("summary"),
                    "datetime": news.get("datetime"),
                }
                formatted_data.append(formatted_news)
            
            await redis.setex(f"finnhub_news_data:{category.value}", 60 * 30, json.dumps(formatted_data))
            return formatted_data
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"}
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}
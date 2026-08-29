import asyncio
import enum
from os import getenv
import httpx
from app.core.dependencies import redis_dependency
import json
from logging import getLogger
from datetime import datetime, timedelta

logger = getLogger(__name__)
NG_STOCK_API_URL = getenv("NG_STOCK_API_URL")
FINNHUB_API_URL = getenv("FINNHUB_API_URL")
FINNHUB_API_KEY = getenv("FINNHUB_API_KEY")


NGN_MARKET_API_URL = getenv("NGN_MARKET_API_URL")
NGN_MARKET_API_KEY = getenv("NGN_MARKET_API_KEY")


class CategoryEnum(str, enum.Enum):
    merger = "merger"
    general = "general"
    forex = "forex"
    crypto = "crypto"


class NGXCategoryEnum(str, enum.Enum):
    markets = "markets"
    corporate_news = "corporate-news"
    economy = "economy"
    industries = "industries"
    technology = "technology"
    personal_finance = "personal-finance"
    product_updates = "product-updates"


async def get_ng_stock_data(redis: redis_dependency):
    pass


async def get_global_news(
    redis: redis_dependency, category: CategoryEnum
) -> list[dict]:
    async with httpx.AsyncClient() as client:
        try:
            result = await redis.get(f"finnhub_news_data:{category.value}")
            if result:
                return json.loads(result)

            response = await client.get(
                f"{FINNHUB_API_URL}/news?category={category.value}&token={FINNHUB_API_KEY}"
            )
            response.raise_for_status()
            raw_data = response.json()

            result = []
            for item in raw_data:
                publised_at = datetime.fromtimestamp(float(item.get("datetime")))
                if publised_at < datetime.now() - timedelta(days=30):
                    continue
                result.append(
                    {
                        "headline": item.get("headline"),
                        "image": item.get("image"),
                        "url": item.get("url"),
                        "categories": [item.get("category")],
                        "published_at": publised_at.isoformat(),
                        "summary": item.get("summary"),
                    }
                )

            await redis.setex(
                f"finnhub_news_data:{category.value}", 60 * 30, json.dumps(result)
            )
            return result
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            }
        except httpx.RequestError as e:
            return {"error": f"Request error occurred: {str(e)}"}


async def get_ngn_news(
    redis: redis_dependency, category: NGXCategoryEnum = NGXCategoryEnum.markets
) -> list[dict]:

    result = await redis.get("ngn_news:" + category.value)
    if result:
        return json.loads(result)

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {NGN_MARKET_API_KEY}"}
        query_params = {"category": category.value}

        logger.info(f"Fetching NGX movers data from API...{headers} {query_params}")

        response = await client.get(
            f"{NGN_MARKET_API_URL}/blog/posts/",
            headers=headers,
            params=query_params,
        )
        response.raise_for_status()
        raw_data = response.json().get("data", {}).get("data", [])
        # change cover-image to image and title to healine

        result = []
        for item in raw_data:
            result.append(
                {
                    "headline": item.get("title"),
                    "image": item.get("cover_image"),
                    "url": item.get("url"),
                    "summary": item.get("excerpt"),
                    "published_at": item.get("published_date"),
                    "categories": [item.get("categories")],
                }
            )

        await redis.setex(
            "ngn_news:" + category.value, 7 * 24 * 60 * 60, json.dumps(result)
        )
        return result

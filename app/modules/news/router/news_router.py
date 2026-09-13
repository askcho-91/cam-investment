from fastapi import APIRouter
from app.core.dependencies import redis_dependency
import enum
from app.modules.news.services.news_services import (
    get_ngn_news,
    get_global_news,
    CategoryEnum,
    NGXCategoryEnum,
)

from ..services.new_digest import get_news_digest

stock_router = APIRouter(prefix="/news", tags=["News"])


@stock_router.get("/ng")
async def get_ng_news_endpoint(redis: redis_dependency, category: NGXCategoryEnum):
    """Get news data from the API"""
    return await get_ngn_news(redis=redis, category=category)


@stock_router.get("/global")
async def get_global_news_endpoint(category: CategoryEnum, redis: redis_dependency):
    """Get news data from the API"""
    return await get_global_news(redis=redis, category=category)


@stock_router.get("/ai/digest")
async def get_news_digest_endpoint(
    redis: redis_dependency,
    force_refresh: bool = False,
):
    """Get AI-generated news digest for a given category"""

    news_items = []
    ## fectch news items from both global and NGN sources
    for category in CategoryEnum:
        try:
            category_items = await get_global_news(redis=redis, category=category)
            if isinstance(category_items, list):
                news_items.extend(category_items[:10])
        except Exception:
            continue
    for category in NGXCategoryEnum:
        try:
            category_items = await get_ngn_news(redis=redis, category=category)
            if isinstance(category_items, list):
                news_items.extend(category_items[:10])
        except Exception:
            continue

    cache_key = "news_digest"
    return await get_news_digest(
        redis=redis,
        news_items=news_items,
        cache_key=cache_key,
        force_refresh=force_refresh,
    )

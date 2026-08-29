from fastapi import APIRouter
from app.core.dependencies import redis_dependency
import enum
from app.modules.news.services.news_services import (
    get_ngn_news,
    get_global_news,
    CategoryEnum,
    NGXCategoryEnum,
)

stock_router = APIRouter(prefix="/news", tags=["News"])


@stock_router.get("/ng")
async def get_ng_news_endpoint(redis: redis_dependency, category: NGXCategoryEnum):
    """Get news data from the API"""
    return await get_ngn_news(redis=redis, category=category)


@stock_router.get("/global")
async def get_global_news_endpoint(category: CategoryEnum, redis: redis_dependency):
    """Get news data from the API"""
    return await get_global_news(redis=redis, category=category)

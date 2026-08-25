from fastapi import APIRouter
from app.core.dependencies import redis_dependency
import enum
from app.modules.news.services.news_services import get_ng_stock_data, get_global_news, CategoryEnum

stock_router = APIRouter(prefix="/news", tags=["News"])




@stock_router.get("/ng")
async def get_ng_stocks(redis: redis_dependency):
    """Get news data from the API"""
    return await get_ng_stock_data(redis=redis)


@stock_router.get("/global")
async def get_global_stocks(category: CategoryEnum, redis: redis_dependency):
    """Get news data from the API"""
    return await get_global_news(redis=redis, category=category)
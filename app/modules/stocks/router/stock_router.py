from fastapi import APIRouter
from app.core.dependencies import redis_dependency
from app.modules.stocks.services.stock_services import get_ng_stock_data, get_multiple_finnhub_stock_data

stock_router = APIRouter(prefix="/stocks", tags=["Stocks"])

GLOBAL_SYMB = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AMD",
    "NFLX",
    "AVGO",
    "ORCL",
    "PLTR",
    "JPM",
    "V",
    "MA",
    "BRK.B",
    "COST",
    "WMT",
    "KO",
    "DIS"
]

@stock_router.get("/ng")
async def get_ng_stocks(redis: redis_dependency):
    """Get stock data from the API"""
    result = await get_ng_stock_data(redis=redis)
    return result["EQUITIES"] if "EQUITIES" in result else result


@stock_router.get("/global")
async def get_global_stocks(redis: redis_dependency):
    """Get stock data from the API"""
    return await get_multiple_finnhub_stock_data(redis=redis, symbols=GLOBAL_SYMB)
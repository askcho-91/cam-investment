from fastapi import APIRouter
from app.core.dependencies import redis_dependency
from app.modules.stocks.services import stock_services
from logging import getLogger
import httpx

logger = getLogger(__name__)
logger.info("Stock router initialized.")

stock_router = APIRouter(prefix="/stocks", tags=["Stocks"])
market_router = APIRouter(prefix="/market", tags=["Market"])

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
    "DIS",
]


@stock_router.get("/ng")
async def get_ng_stocks(redis: redis_dependency):
    """Get stock data from the API"""
    result = await stock_services.get_ng_stock_data(redis=redis)
    return result["EQUITIES"] if "EQUITIES" in result else result


@market_router.get("/ng/bonds")
async def get_ng_bonds(redis: redis_dependency):
    """Get bond data from the API"""
    result = await stock_services.get_ng_stock_data(redis=redis)
    return result["BONDS"] if "BONDS" in result else result


@market_router.get("/ng/etps")
async def get_ng_etps(redis: redis_dependency):
    """Get ETP data from the API"""
    result = await stock_services.get_ng_stock_data(redis=redis)
    return result["ETPS"] if "ETPS" in result else result


@stock_router.get("/global")
async def get_global_stocks(redis: redis_dependency):
    """Get stock data from the API"""
    return await stock_services.get_multiple_finnhub_stock_data(
        redis=redis, symbols=GLOBAL_SYMB
    )


@market_router.get("/ng/movers")
async def get_ng_movers(redis: redis_dependency):
    """Get stock data from the API"""
    try:
        return await stock_services.get_ngn_movers(redis=redis)
    except Exception as e:
        logger.error(f"An error occurred while fetching NGX movers: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


@market_router.get("/global/movers")
async def get_global_movers(redis: redis_dependency):
    """Get stock data from the API"""
    try:
        return await stock_services.get_global_movers(redis=redis)
    except Exception as e:
        logger.error(f"An error occurred while fetching global movers: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


@market_router.get("/ng/indices")
async def get_ng_indices_(redis: redis_dependency):
    """Get stock data from the API"""
    try:
        result = await stock_services.get_ng_indices(redis=redis)
        return result

    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        }
    except httpx.RequestError as e:
        return {"error": f"Request error occurred: {str(e)}"}

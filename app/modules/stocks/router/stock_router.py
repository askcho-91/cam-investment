from fastapi import APIRouter, HTTPException, status
from app.core.dependencies import redis_dependency
from app.modules.stocks.services import stock_services
from app.modules.stocks.services import chart_history
from logging import getLogger
import httpx
from pydantic import BaseModel

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
async def get_global_stocks(redis: redis_dependency, symbols: str | None = None):
    """Get stock data from the API"""
    requested_symbols = (
        [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
        if symbols
        else GLOBAL_SYMB
    )
    return await stock_services.get_multiple_finnhub_stock_data(
        redis=redis, symbols=requested_symbols
    )


@stock_router.get("/global/{symbol}")
async def get_global_stock(symbol: str, redis: redis_dependency):
    """Get stock data from the API"""
    result = await stock_services.get_stock_data_by_symbol(redis=redis, symbol=symbol)
    if result.get("error") or result.get("current_price") is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Global stock not found"
        )
    return result


@stock_router.get("/global/{symbol}/news")
async def get_global_stock_news(symbol: str, redis: redis_dependency):
    result = await stock_services.get_global_company_news(redis=redis, symbol=symbol)
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Company news unavailable"
        )
    return result


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


@market_router.get("/ng/indices/{symbol}/chart")
async def get_ng_index_chart(
    symbol: str,
    redis: redis_dependency,
    period: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    try:
        result = await chart_history.get_index_chart(
            symbol=symbol,
            redis=redis,
            period=period,
            from_date=from_date,
            to_date=to_date,
        )
        return result

    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        }
    except httpx.RequestError as e:
        return {"error": f"Request error occurred: {str(e)}"}


@market_router.get("/ng/companies/profile/{symbol}")
async def get_company_profile_endpoint(symbol: str, redis: redis_dependency):
    try:
        result = await chart_history.get_company_profile(symbol=symbol, redis=redis)
        return result

    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        }
    except httpx.RequestError as e:
        return {"error": f"Request error occurred: {str(e)}"}


@market_router.get("/ng/companies/chart/{symbol}")
async def get_company_chart_endpoint(
    symbol: str,
    redis: redis_dependency,
    period: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    try:
        result = await chart_history.get_company_chart(
            symbol=symbol,
            redis=redis,
            period=period,
            from_date=from_date,
            to_date=to_date,
        )
        return result

    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        }
    except httpx.RequestError as e:
        return {"error": f"Request error occurred: {str(e)}"}


@market_router.get("/ng/forex/{source}")
async def get_forex_endpoint(
    source: str,
    redis: redis_dependency,
    period: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    try:
        result = await chart_history.get_forex_chart(
            source=source,
            target="NGN",
            redis=redis,
            period=period,
            from_date=from_date,
            to_date=to_date,
        )
        return result

    except httpx.HTTPStatusError as e:
        return {
            "error": f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        }
    except httpx.RequestError as e:
        return {"error": f"Request error occurred: {str(e)}"}

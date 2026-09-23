from logging import getLogger
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import redis_dependency
from app.modules.markets.services import (
    commodities_service,
    crypto_service,
    etf_service,
    forex_service,
    indices_service,
    mutual_fund_service,
    search_service,
)

logger = getLogger(__name__)

# Same prefix/tag as the existing `market_router` in the stocks module -
# include both routers on your FastAPI app; FastAPI merges routes that
# share a prefix. Rename this prefix if you'd rather keep them fully
# separate.
markets_router = APIRouter(prefix="/market", tags=["Market"])


def _split_csv(value: Optional[str]) -> Optional[list[str]]:
    return [item.strip() for item in value.split(",")] if value else None


@markets_router.get("/global/forex")
async def get_forex(
    redis: redis_dependency,
    pairs: Optional[str] = Query(
        None,
        description="Comma-separated currency pairs, e.g. 'EUR-USD,GBP-USD'. Defaults to a curated list.",
    ),
):
    """Get forex exchange rates."""
    try:
        parsed_pairs = None
        if pairs:
            parsed_pairs = [tuple(pair.split("-")) for pair in pairs.split(",")]
        return await forex_service.get_forex_rates(redis=redis, pairs=parsed_pairs)
    except Exception as e:
        logger.error(f"An error occurred while fetching forex rates: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}

@markets_router.get("/ng/forex/")
async def get_forex(
    redis: redis_dependency
):
    try:
        return await forex_service.get_ngn_forex_pair(redis)
    except Exception as e:
        logger.error(f"An error occurred while fetching forex rates: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}

@markets_router.get("/global/crypto")
async def get_crypto(
    redis: redis_dependency,
    coins: Optional[str] = Query(
        None,
        description="Comma-separated CoinGecko ids, e.g. 'bitcoin,ethereum'. Defaults to a curated list.",
    ),
    vs_currency: str = "usd",
):
    """Get crypto prices."""
    try:
        return await crypto_service.get_crypto_prices(
            redis=redis, coin_ids=_split_csv(coins), vs_currency=vs_currency
        )
    except Exception as e:
        logger.error(f"An error occurred while fetching crypto prices: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


@markets_router.get("/global/commodities")
async def get_commodities(
    redis: redis_dependency,
    commodities: Optional[str] = Query(
        None,
        description="Comma-separated Alpha Vantage commodity functions, e.g. 'WTI,BRENT'. Defaults to a curated list.",
    ),
):
    """Get commodity prices."""
    try:
        return await commodities_service.get_commodities(
            redis=redis, functions=_split_csv(commodities)
        )
    except Exception as e:
        logger.error(f"An error occurred while fetching commodities: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


@markets_router.get("/global/etfs")
async def get_etfs(
    redis: redis_dependency,
    symbols: Optional[str] = Query(
        None,
        description="Comma-separated ETF tickers, e.g. 'SPY,QQQ'. Defaults to a curated list.",
    ),
):
    """Get ETF quotes."""
    try:
        return await etf_service.get_etf_quotes(
            redis=redis, symbols=_split_csv(symbols)
        )
    except Exception as e:
        logger.error(f"An error occurred while fetching ETF quotes: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


@markets_router.get("/global/mutual-funds")
async def get_mutual_funds(
    redis: redis_dependency,
    symbols: Optional[str] = Query(
        None,
        description="Comma-separated mutual fund tickers. Defaults to a small curated list.",
    ),
):
    """Get mutual fund NAVs."""
    try:
        return await mutual_fund_service.get_mutual_funds(
            redis=redis, symbols=_split_csv(symbols)
        )
    except Exception as e:
        logger.error(f"An error occurred while fetching mutual funds: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


@markets_router.get("/global/indices")
async def get_indices(redis: redis_dependency):
    """Get major global index levels, tracked via their ETF proxies."""
    try:
        return await indices_service.get_indices(redis=redis)
    except Exception as e:
        logger.error(f"An error occurred while fetching indices: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


@markets_router.get("/global/search")
async def search_market(
    redis: redis_dependency,
    q: str = Query(
        ..., min_length=1, description="Search text - a ticker or company/coin name"
    ),
    asset_type: str = Query(
        "stock",
        description="'stock', 'etf', or 'crypto'. Stocks and ETFs share the same Finnhub search.",
    ),
):
    """
    Live symbol search. Returns matches only - it does NOT return prices;
    fetch quotes for the matched tickers/ids separately (via /stocks/global,
    /market/global/etfs, or /market/global/crypto with a symbols/coins
    override) once the user picks a result.

    NG-listed stocks aren't covered - that data source doesn't expose a
    search endpoint. Filter the already-fetched NG stock list client-side instead.
    """
    normalized_type = asset_type.strip().lower()
    if normalized_type not in {"stock", "etf", "crypto"}:
        raise HTTPException(
            status_code=400, detail="asset_type must be stock, etf, or crypto"
        )
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be blank")
    try:
        return await search_service.search(query=q, asset_type=normalized_type)
    except Exception as e:
        logger.error(f"An error occurred while searching: {str(e)}")
        raise HTTPException(
            status_code=502, detail="Market search provider unavailable"
        ) from e

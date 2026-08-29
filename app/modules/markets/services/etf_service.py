from logging import getLogger

from app.core.dependencies import redis_dependency
from app.modules.markets.constants import DEFAULT_ETFS
from app.modules.stocks.services import stock_services

logger = getLogger(__name__)


async def get_etf_quotes(
    redis: redis_dependency, symbols: list[str] | None = None
) -> list[dict] | dict:
    """
    ETFs trade on the same exchanges, with the same quote shape, as
    ordinary equities - so this reuses the existing Finnhub multi-quote
    pipeline from the stocks module instead of spending Alpha Vantage's
    tiny daily budget on data Finnhub already covers well.
    """
    symbols = symbols or DEFAULT_ETFS
    return await stock_services.get_multiple_finnhub_stock_data(redis=redis, symbols=symbols)

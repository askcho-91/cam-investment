from logging import getLogger

from app.core.dependencies import redis_dependency
from app.modules.markets.constants import DEFAULT_INDEX_PROXIES
from app.modules.stocks.services import stock_services

logger = getLogger(__name__)


async def get_indices(
    redis: redis_dependency, proxies: dict[str, str] | None = None
) -> list[dict] | dict:
    """
    Real index tickers (^GSPC, ^DJI, ...) aren't reliably available on
    Alpha Vantage's free tier. Rather than spend budget finding out, each
    major index is tracked via its tracker ETF (see DEFAULT_INDEX_PROXIES)
    through the existing Finnhub pipeline, and labeled as a proxy in the
    response so it's never confused with the index's own level.
    """
    proxies = proxies or DEFAULT_INDEX_PROXIES
    symbols = list(proxies.values())
    quotes = await stock_services.get_multiple_finnhub_stock_data(redis=redis, symbols=symbols)

    if isinstance(quotes, dict) and "error" in quotes:
        return quotes

    quotes_by_symbol = {quote["symbol"]: quote for quote in quotes}
    return [
        {"index": index_name, "proxy_symbol": symbol, **quotes_by_symbol.get(symbol, {})}
        for index_name, symbol in proxies.items()
    ]

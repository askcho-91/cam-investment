"""One-shot price-alert monitor for cron, a worker, or a scheduled job."""

import asyncio
from decimal import Decimal, InvalidOperation

from app.core.db_config import async_session
from app.core.redis_client import get_redis_client
from app.modules.stocks.services.stock_services import (
    get_multiple_finnhub_stock_data,
    get_ng_stock_data,
)
from .alert_services import trigger_matching_alerts

GLOBAL_SYMBOLS = [
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


def _add_quote(quotes: dict, asset_type: str, identifier: str | None, price) -> None:
    if not identifier or price is None:
        return
    try:
        quotes[(asset_type, identifier.strip().upper())] = Decimal(str(price))
    except InvalidOperation, ValueError:
        return


async def collect_quotes(redis) -> dict[tuple[str, str], Decimal]:
    quotes: dict[tuple[str, str], Decimal] = {}

    ng_payload = await get_ng_stock_data(redis)
    if isinstance(ng_payload, dict):
        for category in ng_payload.values():
            if not isinstance(category, list):
                continue
            for item in category:
                _add_quote(
                    quotes, "ng_stock", item.get("symbol"), item.get("current_price")
                )

    global_payload = await get_multiple_finnhub_stock_data(redis, GLOBAL_SYMBOLS)
    if isinstance(global_payload, list):
        for item in global_payload:
            _add_quote(
                quotes, "global_stock", item.get("symbol"), item.get("current_price")
            )

    return quotes


async def run_once() -> int:
    redis = get_redis_client()
    try:
        quotes = await collect_quotes(redis)
        async with async_session() as db:
            triggered = await trigger_matching_alerts(db, quotes)
        return len(triggered)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    print(f"Triggered {asyncio.run(run_once())} price alerts")

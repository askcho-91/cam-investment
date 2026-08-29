# Default symbol/pair sets returned when a request omits an override.
# Every service function accepts an explicit list too, so callers can
# widen or narrow coverage per-request without touching this file.

DEFAULT_FOREX_PAIRS = [
    ("EUR", "USD"),
    ("GBP", "USD"),
    ("USD", "JPY"),
    ("USD", "NGN"),
    ("GBP", "NGN"),
    ("EUR", "NGN"),
]

# CoinGecko coin ids (NOT ticker symbols - CoinGecko's /simple/price keys
# off ids, e.g. "bitcoin", not "BTC")
DEFAULT_CRYPTO_IDS = [
    "bitcoin",
    "ethereum",
    "tether",
    "binancecoin",
    "solana",
    "ripple",
    "usd-coin",
    "cardano",
    "dogecoin",
    "tron",
]

# Alpha Vantage commodities - each is its OWN function/endpoint, there is
# no batch call. ALL_COMMODITIES returns a broad commodity price index.
DEFAULT_COMMODITIES = [
    "WTI",
    "BRENT",
    "NATURAL_GAS",
    "COPPER",
    "ALUMINUM",
    "WHEAT",
    "CORN",
    "COTTON",
    "SUGAR",
    "COFFEE",
    "ALL_COMMODITIES",
]

DEFAULT_ETFS = ["SPY", "QQQ", "DIA", "VOO", "VTI", "IWM", "GLD", "ARKK"]

# Alpha Vantage's mutual fund coverage is thin relative to stocks/ETFs -
# keep the default list small and well-supported.
DEFAULT_MUTUAL_FUNDS = ["VFIAX", "FXAIX", "SWPPX", "VTSAX"]

# Alpha Vantage's free tier does not reliably return raw index tickers
# (^GSPC, ^DJI, ...). We track each index via its tracker ETF instead and
# label the response as a proxy. If you move to a paid plan (or another
# provider) that supports real index quotes, swap the lookup in
# indices_service.py rather than changing this list's shape.
DEFAULT_INDEX_PROXIES = {
    "S&P 500": "SPY",
    "Dow Jones Industrial Average": "DIA",
    "Nasdaq 100": "QQQ",
    "Russell 2000": "IWM",
}

# Cache TTLs, in seconds.
# Forex / commodities / mutual funds / indices all draw from Alpha
# Vantage's shared, tiny free-tier budget (25 requests/day as of writing),
# so they're cached far longer than the 30s used for stock quotes.
FOREX_CACHE_TTL = 3600  # 1 hour
COMMODITIES_CACHE_TTL = 21600  # 6 hours - commodities reprice infrequently
MUTUAL_FUND_CACHE_TTL = 21600  # 6 hours - funds only reprice once/day (NAV)
INDICES_CACHE_TTL = 30  # rides on the existing Finnhub stock-quote TTL
ETF_CACHE_TTL = 30  # rides on the existing Finnhub stock-quote TTL
CRYPTO_CACHE_TTL = 60  # CoinGecko's free tier is generous, refresh faster

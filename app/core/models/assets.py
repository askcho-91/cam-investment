from enum import Enum


class AssetType(str, Enum):
    NG_STOCK = "ng_stock"
    GLOBAL_STOCK = "global_stock"
    FOREX = "forex"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    INDEX = "index"


class AlertDirection(str, Enum):
    ABOVE = "above"
    BELOW = "below"
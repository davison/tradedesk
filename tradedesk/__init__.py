# tradedesk/__init__.py
"""
Tradedesk - Trading infrastructure library for IG Markets.
Copyright 2026 Radius Red Ltd.

Provides authenticated API access, Lightstreamer streaming, and a base
framework for implementing trading strategies.
"""

from .strategy import BaseStrategy
from .runner import run_strategies
from .subscriptions import MarketSubscription, ChartSubscription
from .marketdata import MarketData, Candle, CandleClose, ChartHistory

__version__ = "0.4.0"

__all__ = [
    "__version__",
    "BaseStrategy",
    "run_strategies",
    "MarketData",
    "MarketSubscription",
    "ChartSubscription",
    "Candle",
    "CandleClose",
    "ChartHistory",
]

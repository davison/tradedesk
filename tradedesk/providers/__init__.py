"""
Provider-agnostic interfaces.

This module defines the stable interfaces used by strategies and runners.
Concrete provider implementations (e.g. IG) should implement these contracts.
"""

from ..marketdata import MarketData
from .base import AccountBalance, BrokerPosition, Client, Streamer
from ..marketdata import CandleClose

__all__ = [
    "AccountBalance",
    "BrokerPosition",
    "Client",
    "Streamer",
    "MarketData",
    "CandleClose",
]

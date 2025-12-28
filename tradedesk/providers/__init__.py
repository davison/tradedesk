"""
Provider-agnostic interfaces.

This module defines the stable interfaces used by strategies and runners.
Concrete provider implementations (e.g. IG) should implement these contracts.
"""

from .base import Client, Streamer
from .events import MarketData, CandleClose

__all__ = [
    "Client", 
    "Streamer",
    "MarketData",
    "CandleClose",
]

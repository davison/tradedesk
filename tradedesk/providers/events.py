"""
Provider-neutral market data events.

These events are produced by Streamer implementations and consumed by the
strategy framework. They are not exposed directly to user strategies yet.
"""

from dataclasses import dataclass
from typing import Any

from tradedesk.chartdata import Candle


@dataclass(frozen=True)
class MarketData:
    """Represents a tick-level market update."""
    epic: str
    bid: float
    offer: float
    timestamp: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class CandleClose:
    """Represents a completed OHLCV candle."""
    epic: str
    period: str
    candle: Candle

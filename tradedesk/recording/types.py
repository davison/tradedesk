from dataclasses import dataclass
from enum import Enum


class RecordingMode(Enum):
    BACKTEST = "backtest"
    BROKER = "broker"  # covers both demo and live


@dataclass(frozen=True)
class TradeRecord:
    timestamp: str
    instrument: str
    direction: str  # "BUY" or "SELL"
    size: float     # stake (e.g. £/point)
    price: float    # executed price (IG points)
    reason: str = ""


@dataclass(frozen=True)
class EquityRecord:
    timestamp: str
    equity: float

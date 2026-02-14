"""
Provider-neutral interfaces.

The intent is to keep tradedesk strategies independent from any single broker.
At this stage the interfaces are intentionally small; we will extend them as
we encapsulate streaming and implement backtesting.
"""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class BrokerPosition:
    """Provider-neutral representation of a position held at the broker."""

    instrument: str
    direction: str  # "BUY" or "SELL" (broker-native)
    size: float
    entry_price: float
    deal_id: str
    currency: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class AccountBalance:
    """Provider-neutral snapshot of account funds."""

    balance: float  # total account value
    deposit: float  # margin used
    available: float  # funds available for new positions
    profit_loss: float  # unrealised P&L
    currency: str = ""


class DealRejectedException(Exception):
    """Raised when a deal is not accepted after placing a market order."""

    pass


class Direction(str, Enum):
    """Trading direction for a position.

    Generic concept representing position bias (LONG or SHORT).
    Brokers are responsible for converting this to their API format.
    """

    LONG = "long"
    SHORT = "short"

    def opposite(self) -> "Direction":
        """Return the opposite direction."""
        return Direction.SHORT if self is Direction.LONG else Direction.LONG

    def to_order_side(self) -> str:
        """
        Convert direction to order side string (BUY/SELL).

        This is the standard convention used by most broker APIs and the
        BacktestClient for placing market orders.

        Returns:
            "BUY" for LONG positions, "SELL" for SHORT positions
        """
        return "BUY" if self is Direction.LONG else "SELL"

    @classmethod
    def from_order_side(cls, side: str) -> "Direction":
        """
        Convert order side string (BUY/SELL) to direction.
        """
        if side.upper() == "BUY":
            return Direction.LONG
        elif side.upper() == "SELL":
            return Direction.SHORT
        else:
            raise ValueError(f"Invalid order side {side}: must be BUY or SELL")

"""Broker-agnostic trading types."""

from enum import Enum


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

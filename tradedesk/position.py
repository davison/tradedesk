"""Position tracking utilities."""

from tradedesk.types import Direction
from tradedesk.marketdata import Candle


class PositionTracker:
    """
    Manages position state for trading strategies.

    Tracks:
    - Position direction and size
    - Entry price
    - Bars held in position
    - Maximum favorable excursion (MFE)
    """

    def __init__(self):
        self.direction: Direction | None = None
        self.size: float | None = None
        self.entry_price: float | None = None
        self.bars_held: int = 0
        self.mfe_points: float = 0.0

    def reset(self):
        """Reset all position state to flat."""
        self.direction = None
        self.size = None
        self.entry_price = None
        self.bars_held = 0
        self.mfe_points = 0.0

    def is_flat(self) -> bool:
        """Check if no position is held."""
        return self.direction is None

    def open(self, direction: Direction, size: float, entry_price: float):
        """
        Open a new position.

        Args:
            direction: Position direction (LONG or SHORT)
            size: Position size
            entry_price: Entry price
        """
        self.direction = direction
        self.size = size
        self.entry_price = entry_price
        self.bars_held = 0
        self.mfe_points = 0.0

    def update_mfe(self, candle: Candle):
        """
        Update maximum favorable excursion using candle extremes.

        Args:
            candle: Current candle with high/low data
        """
        if self.entry_price is None or self.direction is None:
            return

        if self.direction == Direction.LONG:
            favorable = float(candle.high) - self.entry_price
        else:
            favorable = self.entry_price - float(candle.low)

        self.mfe_points = max(self.mfe_points, favorable)

    def current_pnl_points(self, close_price: float) -> float:
        """
        Calculate current PnL in points.

        Args:
            close_price: Current close price

        Returns:
            PnL in points (positive for profit, negative for loss)
        """
        if self.entry_price is None or self.direction is None:
            return 0.0

        if self.direction == Direction.LONG:
            return close_price - self.entry_price
        else:
            return self.entry_price - close_price

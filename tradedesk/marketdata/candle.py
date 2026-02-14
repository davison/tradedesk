from dataclasses import dataclass


@dataclass
class Candle:
    """
    Represents a single OHLCV candle.

    Attributes:
        timestamp: ISO 8601 timestamp or Unix timestamp string
        open: Opening price
        high: Highest price during period
        low: Lowest price during period
        close: Closing price
        volume: Trading volume (or 0 if unavailable)
        tick_count: Number of ticks/updates during period
    """

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    tick_count: int = 0

    @property
    def typical_price(self) -> float:
        """
        Calculate typical price (HLC/3).
        Used in Money Flow Index and other volume-weighted indicators.
        """
        return (self.high + self.low + self.close) / 3

    @property
    def mid(self) -> float:
        """Calculate midpoint between high and low."""
        return (self.high + self.low) / 2

    @property
    def range(self) -> float:
        """Calculate candle range (high - low)."""
        return self.high - self.low

    def __repr__(self) -> str:
        return (
            f"Candle(timestamp={self.timestamp}, "
            f"O={self.open:.5f}, H={self.high:.5f}, "
            f"L={self.low:.5f}, C={self.close:.5f}, "
            f"V={self.volume:.0f})"
        )
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np

@dataclass(frozen=True)
class Instrument:
    """
    A standardized, immutable representation of a tradable financial asset.

    This class serves as a universal identifier to replace broker-specific 
    strings (such as IG Group's 'EPIC'). It centralizes common identifiers 
    like ISIN and RIC while allowing for a mapping of specific codes used 
    by different provider APIs.

    Attributes:
        symbol: The primary ticker or shorthand identifier (e.g., 'AAPL' or 'GBPUSD').
            This is the only required field.
        isin: The International Securities Identification Number (12-character code).
        ric: The Reuters Instrument Code (e.g., 'AAPL.O').
        name: The full human-readable name of the instrument (e.g., 'Apple Inc').
        asset_class: The category of the instrument (e.g., 'FX', 'Equity', 'Future').
        broker_codes: A mapping of broker names to their specific internal identifiers.
            Example: {'ig': 'CS.D.GBPUSD.TODAY.IP', 'ibkr': 'GBP.USD'}

    Example:
        >>> aapl = Instrument(symbol="AAPL", isin="US0378331005", asset_class="Equity")
        >>> print(aapl)
        AAPL
    """
    symbol: str
    isin: Optional[str] = None
    ric: Optional[str] = None
    name: Optional[str] = None
    asset_class: Optional[str] = None
    # We use a default_factory because a dict is a mutable object.
    # This ensures every instance gets its own unique dictionary.
    broker_codes: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Validates the instrument. Checks ISIN format and checksum.
        """
        if self.isin is not None:
            self._validate_isin(self.isin)

    def _validate_isin(self, isin: str) -> None:
        """
        Validates the ISIN format and checksum using the Luhn algorithm.
        Raises ValueError if invalid.
        """
        # 1. Basic Format Check: 2 letters, 9 alphanumeric, 1 digit
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
            raise ValueError(
                f"Invalid ISIN format for {self.symbol}: '{isin}'. "
                "Expected 2 letters, 9 alphanumeric, and 1 digit."
            )

        # 2. Convert letters to digits (A=10, B=11, ..., Z=35)
        digits_str = "".join(
            str(int(char, 36)) if char.isalpha() else char for char in isin
        )

        # 3. Apply Luhn Algorithm
        digits = [int(d) for d in digits_str]
        checksum_sum = 0
        
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                doubled = digit * 2
                checksum_sum += doubled if doubled < 10 else doubled - 9
            else:
                checksum_sum += digit

        if checksum_sum % 10 != 0:
            raise ValueError(f"ISIN checksum failed for {self.symbol}: '{isin}'.")
    
    def __str__(self) -> str:
        return self.symbol

    def __repr__(self) -> str:
        return f"Instrument(symbol={self.symbol!r}, isin={self.isin!r})"


@dataclass(frozen=True)
class MarketData:
    """Represents a tick-level market update."""

    instrument: str
    bid: float
    offer: float
    timestamp: str
    raw: dict[str, Any]


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


@dataclass(frozen=True)
class CandleClose:
    """Represents a completed OHLCV candle."""

    instrument: str
    period: str
    candle: Candle


class ChartHistory:
    """
    Maintains a rolling window of candles for a specific instrument/timeframe pair.

    Provides convenient access to price arrays needed for indicator calculations.
    Automatically manages memory by limiting history length.

    Example:
        history = ChartHistory("CS.D.GBPUSD.TODAY.IP", "5MINUTE", max_length=200)
        history.add_candle(candle)

        # Get arrays for indicator calculation
        closes = history.get_closes()
        highs = history.get_highs(count=20)  # Last 20 candles only
    """

    def __init__(self, instrument: str, period: str, max_length: int = 200):
        """
        Initialize chart history.

        Args:
            instrument: Instrument identifier
            period: Timeframe (e.g., "5MINUTE", "HOUR")
            max_length: Maximum number of candles to retain
        """
        self.instrument = instrument
        self.period = period
        self.max_length = max_length
        self.candles: deque[Candle] = deque(maxlen=max_length)

    def add_candle(self, candle: Candle) -> None:
        """
        Add a new candle to history.

        Automatically removes oldest candle if at max_length.
        """
        self.candles.append(candle)

    def get_candles(self, count: Optional[int] = None) -> list[Candle]:
        """
        Get candle objects.

        Args:
            count: Number of most recent candles to return (None = all)

        Returns:
            List of Candle objects, oldest first
        """
        if count is None:
            return list(self.candles)
        return list(self.candles)[-count:]

    def get_opens(self, count: Optional[int] = None) -> np.ndarray:
        """Get array of opening prices."""
        candles = self.get_candles(count)
        return np.array([c.open for c in candles], dtype=np.float64)

    def get_highs(self, count: Optional[int] = None) -> np.ndarray:
        """Get array of high prices."""
        candles = self.get_candles(count)
        return np.array([c.high for c in candles], dtype=np.float64)

    def get_lows(self, count: Optional[int] = None) -> np.ndarray:
        """Get array of low prices."""
        candles = self.get_candles(count)
        return np.array([c.low for c in candles], dtype=np.float64)

    def get_closes(self, count: Optional[int] = None) -> np.ndarray:
        """Get array of closing prices."""
        candles = self.get_candles(count)
        return np.array([c.close for c in candles], dtype=np.float64)

    def get_volumes(self, count: Optional[int] = None) -> np.ndarray:
        """Get array of volumes."""
        candles = self.get_candles(count)
        return np.array([c.volume for c in candles], dtype=np.float64)

    def get_tick_counts(self, count: Optional[int] = None) -> np.ndarray:
        """Get array of tick counts (volume proxy for forex)."""
        candles = self.get_candles(count)
        return np.array([c.tick_count for c in candles], dtype=np.int64)

    def get_typical_prices(self, count: Optional[int] = None) -> np.ndarray:
        """Get array of typical prices (HLC/3)."""
        candles = self.get_candles(count)
        return np.array([c.typical_price for c in candles], dtype=np.float64)

    @property
    def latest(self) -> Optional[Candle]:
        """Get the most recent candle, or None if empty."""
        return self.candles[-1] if self.candles else None

    def __len__(self) -> int:
        """Return number of candles in history."""
        return len(self.candles)

    def __repr__(self) -> str:
        return (
            f"ChartHistory(instrument={self.instrument}, period={self.period}, "
            f"candles={len(self)}/{self.max_length})"
        )

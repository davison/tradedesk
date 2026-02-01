"""Portfolio types and protocols."""

from dataclasses import dataclass
from typing import NewType, Any, Protocol


Instrument = NewType("Instrument", str)


@dataclass(frozen=True)
class CandleCloseEvent:
    """Event representing a candle close for an instrument."""
    instrument: Instrument
    period: str
    candle: Any  # Keep client-agnostic; strategies know their Candle type


@dataclass(frozen=True)
class StrategySpec:
    """
    A strategy binding plus metadata required by portfolio orchestrators.
    """
    instrument: str
    period: str
    strategy_cls: type
    kwargs: dict[str, Any]


class PortfolioStrategy(Protocol):
    """Protocol for strategies managed by PortfolioRunner."""

    instrument: Instrument

    def set_risk_per_trade(self, value: float) -> None:
        """Set the strategy's per-trade risk budget."""
        ...

    def is_regime_active(self) -> bool:
        """Return True if strategy's regime is currently active."""
        ...

    async def on_candle_close(self, event: CandleCloseEvent) -> None:
        """Process a candle close event."""
        ...

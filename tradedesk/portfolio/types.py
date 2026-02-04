"""Core types and protocols for portfolio-level strategy management.

This module defines the data structures and interfaces used by the
`PortfolioRunner` to orchestrate multiple strategies across different
instruments.
"""

from dataclasses import dataclass
from typing import NewType, Any, Protocol


__all__ = [
    "CandleCloseEvent",
    "Instrument",
    "PortfolioStrategy",
    "StrategySpec",
]


Instrument = NewType("Instrument", str)


@dataclass(frozen=True)
class CandleCloseEvent:
    """Event representing a completed candle for a specific instrument and period.

    This event is dispatched by the portfolio orchestrator to the relevant
    strategy instance.

    Attributes:
        instrument: The instrument for which the candle closed.
        period: The timeframe of the candle (e.g., "15MINUTE").
        candle: The completed candle object. The type is `Any` to remain
            agnostic of the specific `Candle` implementation used by
            the strategy or backtester.
    """
    instrument: Instrument
    period: str
    candle: Any  # Keep client-agnostic; strategies know their Candle type


@dataclass(frozen=True)
class StrategySpec:
    """Specification for a single strategy instance within a portfolio.

    This dataclass binds a strategy class to a specific instrument and period,
    along with its configuration. The `PortfolioRunner` uses a list of these
    specs to construct the portfolio.

    Attributes:
        instrument: The instrument identifier (e.g., an IG epic).
        period: The chart timeframe for the strategy (e.g., "15MINUTE").
        strategy_cls: The strategy class to instantiate.
        kwargs: A dictionary of keyword arguments to pass to the strategy's
            `__init__` method during instantiation.
    """
    instrument: str
    period: str
    strategy_cls: type
    kwargs: dict[str, Any]


class PortfolioStrategy(Protocol):
    """Protocol defining the interface for strategies managed by `PortfolioRunner`.

    A class implementing this protocol can be managed as part of a larger
    portfolio, receiving risk budget updates and candle events from an
    orchestrator.
    """

    instrument: Instrument

    def set_risk_per_trade(self, value: float) -> None:
        """Set the strategy's per-trade risk budget.

        This is called by the `PortfolioRunner` before each candle event,
        allowing the portfolio's risk policy to dynamically allocate risk.

        Args:
            value: The monetary amount to risk on the next trade.
        """
        ...

    def is_regime_active(self) -> bool:
        """Check if the strategy's underlying trading regime is currently active.

        The `PortfolioRunner` uses this to determine the set of "active"
        strategies for risk allocation purposes.

        Returns:
            True if the regime is active, False otherwise.
        """
        ...

    async def on_candle_close(self, event: CandleCloseEvent) -> None:
        """Process a candle close event for the strategy's instrument.

        This is the primary entry point for the strategy's trading logic.

        Args:
            event: The `CandleCloseEvent` containing the completed candle.
        """
        ...

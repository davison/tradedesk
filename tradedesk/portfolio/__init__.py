"""Portfolio management for multi-instrument trading."""

from .config import BacktestPortfolioConfig, LivePortfolioConfig, PortfolioConfig
from .metrics_tracker import InstrumentWindow, WeightedRollingTracker
from .reconciliation import (
    DiscrepancyType,
    ReconciliationEntry,
    ReconciliationResult,
    reconcile,
)
from .risk import EqualSplitRiskPolicy, RiskAllocationPolicy, atr_normalised_size
from .runner import PortfolioRunner
from .types import (
    CandleCloseEvent,
    Instrument,
    PortfolioStrategy,
    StrategySpec,
)

__all__ = [
    "BacktestPortfolioConfig",
    "CandleCloseEvent",
    "DiscrepancyType",
    "EqualSplitRiskPolicy",
    "Instrument",
    "InstrumentWindow",
    "LivePortfolioConfig",
    "PortfolioConfig",
    "PortfolioRunner",
    "PortfolioStrategy",
    "ReconciliationEntry",
    "ReconciliationResult",
    "RiskAllocationPolicy",
    "StrategySpec",
    "WeightedRollingTracker",
    "atr_normalised_size",
    "reconcile",
]

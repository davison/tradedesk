"""Portfolio management for multi-instrument trading."""

from .config import BacktestPortfolioConfig, LivePortfolioConfig, PortfolioConfig
from .metrics_tracker import InstrumentWindow, WeightedRollingTracker
from .reconciliation import (
    DiscrepancyType,
    ReconciliationEntry,
    ReconciliationResult,
    reconcile,
)
from .fixed_allocation import FixedAllocationRiskPolicy
from .performance_weighted import PerformanceWeightedRiskPolicy
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
    "FixedAllocationRiskPolicy",
    "Instrument",
    "InstrumentWindow",
    "LivePortfolioConfig",
    "PerformanceWeightedRiskPolicy",
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

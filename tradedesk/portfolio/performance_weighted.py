"""Performance-weighted risk allocation policy."""

import logging
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from tradedesk.portfolio.risk import RiskAllocationPolicy
from tradedesk.portfolio.types import Instrument

from tradedesk.portfolio.metrics_tracker import WeightedRollingTracker

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PerformanceWeightedRiskPolicy(RiskAllocationPolicy):
    """
    Allocate risk based on weighted historical performance using a sliding window.

    Uses a recency-weighted rolling window approach where recent trades are weighted
    more heavily than older trades. The policy maintains a continuous sliding window
    that naturally incorporates new data and drops old data.

    At startup, the window is initialized with recent backtest trades. During live
    trading, the window slides forward as new trades occur, providing continuous
    adaptation while maintaining statistical significance.

    Example allocation with 3 instruments:
        - USD/JPY: return/risk = 0.5 -> score = 0.5
        - AUD/JPY: return/risk = 0.3 -> score = 0.3
        - AUD/NZD: return/risk = 0.1 -> score = 0.1

        Total score = 0.9
        Min allocation per instrument = 10% * 10.0 = 1.0
        Reserved = 3.0, Remaining = 7.0

        USD/JPY gets: 1.0 + (0.5/0.9 * 7.0) = 4.89
        AUD/JPY gets: 1.0 + (0.3/0.9 * 7.0) = 3.33
        AUD/NZD gets: 1.0 + (0.1/0.9 * 7.0) = 1.78

    Attributes:
        portfolio_risk_budget: Total risk budget to allocate across instruments
        min_allocation_pct: Minimum allocation per instrument as fraction (0-1)
        tracker: WeightedRollingTracker maintaining the sliding window
        min_trades_required: Minimum trades per instrument to activate performance weighting.
                           Falls back to equal split if any instrument has fewer trades.
                           Default: 100 trades per instrument.
        log_threshold_pct: Only log at INFO level when allocation changes by this percentage.
                          Default: 0.05 (5%). Set to 0.0 to always log at INFO.
    """

    portfolio_risk_budget: float
    min_allocation_pct: float
    tracker: Optional[WeightedRollingTracker] = None
    # Alternative config if `tracker` is not supplied: allow building tracker
    window_size: int = 1500
    decay_weights: Tuple[float, float, float] = (0.60, 0.30, 0.10)
    recompute_interval: int = 50
    historical_data_dir: Optional[str] = None
    min_trades_required: int = 100
    log_threshold_pct: float = 0.05

    def __post_init__(self):
        """Initialize mutable cache for last allocation (bypassing frozen dataclass)."""
        # Use object.__setattr__ to set mutable state on frozen dataclass
        object.__setattr__(self, '_last_allocation', {})
        # If no tracker provided, build one from config fields
        if getattr(self, 'tracker', None) is None:
            try:
                tracker = WeightedRollingTracker(
                    window_size=int(self.window_size),
                    decay_weights=tuple(self.decay_weights),
                    recompute_interval=int(self.recompute_interval),
                )
            except Exception as e:
                log.warning(f"Failed creating internal tracker: {e}")
                tracker = None

            if tracker is not None and self.historical_data_dir:
                try:
                    from pathlib import Path

                    p = Path(self.historical_data_dir)
                    if not p.is_absolute():
                        p = Path.cwd() / p
                    tracker.load_from_backtest(p)
                    log.info(f"Loaded performance window from {p}")
                except FileNotFoundError as e:
                    log.warning(f"Could not load historical data: {e}")
                    log.warning("Policy will start with no historical context")

            object.__setattr__(self, 'tracker', tracker)

    def allocate(self, active_instruments: list[Instrument]) -> Mapping[Instrument, float]:
        """
        Allocate risk budget across active instruments based on weighted performance.

        Falls back to equal split if:
        - Any instrument has fewer than min_trades_required trades
        - All performance scores are negative/zero
        - Minimum allocation constraints cannot be satisfied

        Args:
            active_instruments: List of instruments with active regimes

        Returns:
            Mapping of instrument to allocated risk amount (risk_per_trade)
        """
        if not active_instruments:
            return {}

        k = len(active_instruments)

        # Get weighted performance metrics from tracker
        metrics = self.tracker.compute_metrics(active_instruments)

        # Check if we have sufficient data for performance-based allocation
        insufficient_data = []
        for inst in active_instruments:
            metric = metrics.get(inst)
            if metric is None or metric['total_trades'] < self.min_trades_required:
                trade_count = metric['total_trades'] if metric else 0
                insufficient_data.append((str(inst), trade_count))

        if insufficient_data:
            # Fall back to equal split and log clearly
            per = float(self.portfolio_risk_budget) / float(k)

            instruments_str = ", ".join(
                f"{name} ({count} trades)"
                for name, count in insufficient_data
            )

            log.debug(
                f"Insufficient trade history for performance-weighted allocation. "
                f"Required: {self.min_trades_required} trades per instrument. "
                f"Instruments below threshold: {instruments_str}. "
                f"Falling back to equal split allocation."
            )

            return {inst: per for inst in active_instruments}

        # Calculate performance scores (return/risk ratio, clipped to non-negative)
        scores: dict[Instrument, float] = {}

        for inst in active_instruments:
            metric = metrics[inst]  # We know all exist due to check above

            # Use return/risk ratio, clipped to non-negative
            # Negative performance gets zero score
            ratio = metric['return_to_risk_ratio']
            scores[inst] = max(0.0, ratio)

        # If all scores are zero/negative, fall back to equal split
        total_score = sum(scores.values())

        if total_score <= 0.0:
            per = float(self.portfolio_risk_budget) / float(k)

            log.debug(
                "All instruments have non-positive performance scores. "
                "Falling back to equal split allocation."
            )

            return {inst: per for inst in active_instruments}

        # Apply minimum allocation constraint
        min_per_instrument = self.portfolio_risk_budget * self.min_allocation_pct
        reserved = min_per_instrument * k
        remaining = self.portfolio_risk_budget - reserved

        # If remaining is negative, minimum constraints can't be satisfied
        # Fall back to equal split
        if remaining < 0:
            per = float(self.portfolio_risk_budget) / float(k)

            log.warning(
                f"Minimum allocation constraints cannot be satisfied "
                f"({k} instruments × {min_per_instrument:.2f} min = {reserved:.2f} > {self.portfolio_risk_budget:.2f} budget). "
                f"Falling back to equal split allocation."
            )

            return {inst: per for inst in active_instruments}

        # Normalize scores to weights
        weights = {inst: score / total_score for inst, score in scores.items()}

        # Allocate: minimum + proportional share of remaining
        allocation: dict[Instrument, float] = {}

        for inst in active_instruments:
            allocation[inst] = min_per_instrument + (remaining * weights[inst])

        # Check if allocations have changed significantly
        allocation_changed = self._has_allocation_changed(allocation)

        # Log at INFO level only when allocations change significantly,
        # otherwise DEBUG (allocate() is called on every candle)
        alloc_summary = ", ".join(
            f"{str(inst)}: {allocation[inst]:.2f} (score: {scores[inst]:.3f})"
            for inst in active_instruments
        )

        if allocation_changed:
            log.info(f"Performance-weighted allocation CHANGED: {alloc_summary}")
        else:
            log.debug(f"Performance-weighted allocation: {alloc_summary}")

        # Cache this allocation for next comparison
        object.__setattr__(self, '_last_allocation', allocation.copy())

        return allocation

    def _has_allocation_changed(self, new_allocation: dict[Instrument, float]) -> bool:
        """
        Check if allocation has changed significantly from last time.

        Returns True if:
        - This is the first allocation (no cached allocation)
        - Set of instruments has changed
        - Any allocation changed by more than log_threshold_pct
        """
        last = getattr(self, '_last_allocation', {})

        if not last:
            return True  # First allocation

        # Check if instrument set changed
        if set(new_allocation.keys()) != set(last.keys()):
            return True

        # Check if any allocation changed by more than threshold
        for inst, new_val in new_allocation.items():
            old_val = last.get(inst, 0.0)
            if old_val == 0.0:
                continue  # Avoid division by zero

            pct_change = abs(new_val - old_val) / old_val
            if pct_change > self.log_threshold_pct:
                return True

        return False

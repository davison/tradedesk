"""Fixed-weight risk allocation policy."""

import logging
from typing import Mapping, Dict, Any

from tradedesk.portfolio.risk import RiskAllocationPolicy
from tradedesk.portfolio.types import Instrument

log = logging.getLogger(__name__)


class FixedAllocationRiskPolicy(RiskAllocationPolicy):
    """Allocate risk according to fixed, configured allocations.

    The policy is configured by passing instrument keys as kwargs to the
    constructor (this matches the YAML `params` mapping). Example:

        FixedAllocationRiskPolicy(portfolio_risk_budget=10.0, USDJPY=0.4, GBPUSD=0.6)

    Semantics:
    - The provided values are relative weights (typically sum to 1.0).
    - When a subset of instruments is active, weights are renormalized among
      the active subset and the portfolio budget is distributed accordingly.
    - Unknown active instruments (not present in the configured mapping) are
      ignored. If none of the active instruments are configured, the policy
      falls back to equal-split across active instruments.
    """

    def __init__(self, portfolio_risk_budget: float, **allocations: Any) -> None:

        log.debug(f"Configuring FixedAllocationRiskPolicy with budget: {portfolio_risk_budget}")

        if portfolio_risk_budget is None:
            raise ValueError("portfolio_risk_budget is required")

        self.portfolio_risk_budget = float(portfolio_risk_budget)

        # allocations keys are instrument identifiers (strings) mapping to weights
        raw: Dict[str, float] = {}
        for k, v in allocations.items():
            try:
                raw[str(k)] = float(v)
            except Exception:
                raise ValueError(f"Invalid allocation value for {k!r}: {v!r}")

        if not raw:
            raise ValueError("FixedAllocationRiskPolicy requires at least one allocation entry")

        # Normalize negatives/zeros: only keep positive weights
        positive = {k: w for k, w in raw.items() if w > 0.0}
        if not positive:
            raise ValueError("At least one allocation weight must be > 0")

        total = sum(positive.values())
        # Store base weights normalized to sum to 1.0
        self._base_weights: Dict[Instrument, float] = {
            Instrument(k): (w / total) for k, w in positive.items()
        }

        log.debug(f"base weights: {self._base_weights}")

    def allocate(self, active_instruments: list[Instrument]) -> Mapping[Instrument, float]:
        """Allocate the portfolio risk budget among the active instruments.

        - If `active_instruments` is empty, returns an empty dict.
        - Only instruments present in the configured mapping participate.
        - If none of the active instruments are configured, fall back to an
          equal-split across the active instruments.
        """
        if not active_instruments:
            return {}

        # Determine intersection of active instruments with configured weights
        configured_active = [inst for inst in active_instruments if inst in self._base_weights]

        if not configured_active:
            # No configured instruments active: equal split across active set
            k = len(active_instruments)
            per = float(self.portfolio_risk_budget) / float(k)
            return {inst: per for inst in active_instruments}

        # Renormalize weights among configured_active
        total_weight = sum(self._base_weights[inst] for inst in configured_active)
        if total_weight <= 0:
            # Defensive fallback to equal split across configured_active
            k = len(configured_active)
            per = float(self.portfolio_risk_budget) / float(k)
            return {inst: per for inst in configured_active}

        allocation: Dict[Instrument, float] = {}
        for inst in configured_active:
            weight = self._base_weights[inst] / total_weight
            allocation[inst] = weight * self.portfolio_risk_budget

        return allocation

"""Portfolio orchestration."""

from dataclasses import dataclass

from tradedesk.portfolio.types import CandleCloseEvent, Instrument, PortfolioStrategy
from tradedesk.portfolio.policy import RiskAllocationPolicy


@dataclass
class PortfolioRunner:
    """
    Client-agnostic portfolio orchestrator.

    Responsibilities:
      - Maintain a set of per-instrument strategies
      - Compute active set k from strategy state (previous close)
      - Apply risk policy before processing the next candle close
      - Forward candle events to the relevant strategy

    Does NOT:
      - Place orders (strategies + their clients do that)
      - Perform portfolio rebalancing
      - Attempt to increase utilisation
    """
    strategies: dict[Instrument, PortfolioStrategy]
    policy: RiskAllocationPolicy
    default_risk_per_trade: float

    def _active_instruments(self) -> list[Instrument]:
        """Get list of instruments with active regimes."""
        return [inst for inst, s in self.strategies.items() if s.is_regime_active()]

    def _apply_risk_budgets(self) -> None:
        """Apply risk allocation policy to all strategies."""
        active = self._active_instruments()
        alloc = self.policy.allocate(active)

        # If no regimes active, revert to default risk for all strategies.
        if not alloc:
            for s in self.strategies.values():
                s.set_risk_per_trade(float(self.default_risk_per_trade))
            return

        # If some active, set active strategies to allocated risk,
        # inactive strategies to default (so if they activate this bar, they use default for now).
        for inst, s in self.strategies.items():
            if inst in alloc:
                s.set_risk_per_trade(float(alloc[inst]))
            else:
                s.set_risk_per_trade(float(self.default_risk_per_trade))

    async def on_candle_close(self, event: CandleCloseEvent) -> None:
        """
        Process a candle close event.

        Applies risk budgets before forwarding to the relevant strategy.

        Args:
            event: Candle close event with instrument, period, and candle data
        """
        # Apply risk budgets based on portfolio state *before* processing this bar.
        self._apply_risk_budgets()

        strat = self.strategies.get(event.instrument)
        if strat is None:
            return

        await strat.on_candle_close(event)

# Portfolio Management Guide

The `tradedesk.portfolio` module provides a framework for managing multiple instruments with automated risk allocation.

## Core Concepts

### Portfolio Runner

The `PortfolioRunner` is a client-agnostic orchestrator that:
- Manages multiple strategies across different instruments
- Dynamically allocates risk based on regime activity
- Routes candle events to the appropriate strategies

```python
from tradedesk.portfolio import PortfolioRunner, EqualSplitRiskPolicy, Instrument

# Create strategies for different instruments
strategies = {
    Instrument("EURUSD"): eurusd_strategy,
    Instrument("GBPUSD"): gbpusd_strategy,
    Instrument("USDJPY"): usdjpy_strategy,
}

# Create portfolio runner with risk policy
runner = PortfolioRunner(
    strategies=strategies,
    policy=EqualSplitRiskPolicy(portfolio_risk_budget=100.0),
    default_risk_per_trade=10.0,
)

# Process candle events
await runner.on_candle_close(candle_event)
```

### Portfolio Strategy Protocol

Strategies managed by the portfolio must implement the `PortfolioStrategy` protocol:

```python
from tradedesk.portfolio import PortfolioStrategy, CandleCloseEvent, Instrument

class MyStrategy:
    def __init__(self, instrument: str):
        self.instrument = Instrument(instrument)
        self._risk_per_trade = 10.0
        self._regime_active = False

    def set_risk_per_trade(self, value: float) -> None:
        """Called by PortfolioRunner to set risk allocation."""
        self._risk_per_trade = value

    def is_regime_active(self) -> bool:
        """Return True if strategy's regime is active."""
        return self._regime_active

    async def on_candle_close(self, event: CandleCloseEvent) -> None:
        """Process candle close event."""
        # Strategy logic here
        pass
```

## Risk Allocation Policies

### Equal Split Policy

The `EqualSplitRiskPolicy` divides a fixed portfolio risk budget equally across all instruments with active regimes:

```python
from tradedesk.portfolio import EqualSplitRiskPolicy, Instrument

policy = EqualSplitRiskPolicy(portfolio_risk_budget=100.0)

# If 2 instruments are active, each gets 50.0
active = [Instrument("EURUSD"), Instrument("GBPUSD")]
allocation = policy.allocate(active)
# Returns: {Instrument("EURUSD"): 50.0, Instrument("GBPUSD"): 50.0}

# If 0 instruments are active, returns empty dict
allocation = policy.allocate([])
# Returns: {}
```

### Custom Policies

You can create custom risk allocation policies:

```python
from dataclasses import dataclass
from typing import Mapping
from tradedesk.portfolio.types import Instrument

@dataclass(frozen=True)
class VolatilityWeightedPolicy:
    """Allocate more risk to less volatile instruments."""
    portfolio_risk_budget: float
    volatilities: dict[Instrument, float]

    def allocate(self, active_instruments: list[Instrument]) -> Mapping[Instrument, float]:
        if not active_instruments:
            return {}

        # Calculate inverse volatility weights
        inv_vols = {inst: 1.0 / self.volatilities[inst] for inst in active_instruments}
        total_weight = sum(inv_vols.values())

        # Allocate proportionally
        return {
            inst: (inv_vols[inst] / total_weight) * self.portfolio_risk_budget
            for inst in active_instruments
        }
```

## Risk Allocation Flow

The `PortfolioRunner` applies risk budgets **before** processing each candle:

1. Check which strategies have active regimes (`is_regime_active()`)
2. Apply policy to allocate risk across active instruments
3. Call `set_risk_per_trade()` on each strategy
4. Forward the candle event to the relevant strategy

**Inactive strategies** receive the `default_risk_per_trade` value, so if they activate mid-session, they have a reasonable default.

## Complete Example

```python
from tradedesk.portfolio import (
    PortfolioRunner,
    EqualSplitRiskPolicy,
    CandleCloseEvent,
    Instrument,
)
from tradedesk.marketdata import Candle

class SimpleStrategy:
    def __init__(self, instrument: str, threshold: float):
        self.instrument = Instrument(instrument)
        self.threshold = threshold
        self._risk_per_trade = 10.0
        self._regime_active = False
        self._price_history = []

    def set_risk_per_trade(self, value: float) -> None:
        self._risk_per_trade = value

    def is_regime_active(self) -> bool:
        return self._regime_active

    async def on_candle_close(self, event: CandleCloseEvent) -> None:
        candle = event.candle
        self._price_history.append(candle.close)

        # Simple volatility regime: activate if price moves > threshold
        if len(self._price_history) >= 2:
            move = abs(candle.close - self._price_history[-2])
            self._regime_active = move > self.threshold

# Create strategies
strategies = {
    Instrument("EURUSD"): SimpleStrategy("EURUSD", threshold=0.001),
    Instrument("GBPUSD"): SimpleStrategy("GBPUSD", threshold=0.002),
}

# Create runner
runner = PortfolioRunner(
    strategies=strategies,
    policy=EqualSplitRiskPolicy(portfolio_risk_budget=100.0),
    default_risk_per_trade=50.0,
)

# Process events
candle = Candle(timestamp="1234567890000", open=1.1000, high=1.1050,
                low=1.0950, close=1.1020)
await runner.on_candle_close(
    CandleCloseEvent(
        instrument=Instrument("EURUSD"),
        period="15MINUTE",
        candle=candle,
    )
)
```

## Best Practices

1. **Set appropriate default risk**: The `default_risk_per_trade` should be large enough for strategies to operate if they activate independently.

2. **Monitor active count**: Track how many instruments are typically active to size your `portfolio_risk_budget` appropriately.

3. **Implement clear regime logic**: The `is_regime_active()` method should have clear, testable conditions.

4. **Test policies**: Write tests for your custom policies to ensure they behave correctly with 0, 1, or many active instruments.

5. **Handle edge cases**: Consider what happens when all strategies are inactive, or when one strategy dominates.

## See Also

- [Strategy Guide](strategy_guide.md) - Building trading strategies
- [Risk Management](risk_management.md) - Position sizing utilities
- [Backtesting Guide](backtesting_guide.md) - Testing portfolio strategies

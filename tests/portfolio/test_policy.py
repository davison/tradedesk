"""Tests for portfolio risk allocation policies."""

from tradedesk.portfolio.policy import EqualSplitRiskPolicy
from tradedesk.portfolio.types import Instrument


def test_equal_split_allocates_per_active_instrument():
    """Test that EqualSplitRiskPolicy divides budget equally across active instruments."""
    p = EqualSplitRiskPolicy(portfolio_risk_budget=10.0)

    # No active instruments -> empty allocation
    assert p.allocate([]) == {}

    # One active instrument -> gets full budget
    a = p.allocate([Instrument("EURUSD")])
    assert a[Instrument("EURUSD")] == 10.0

    # Two active instruments -> split equally
    ab = p.allocate([Instrument("EURUSD"), Instrument("GBPUSD")])
    assert ab[Instrument("EURUSD")] == 5.0
    assert ab[Instrument("GBPUSD")] == 5.0

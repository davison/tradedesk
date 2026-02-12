"""Tests for broker-agnostic trading types."""


from tradedesk.execution.broker import Direction


def test_direction_opposite():
    """Test Direction.opposite() method."""
    assert Direction.LONG.opposite() == Direction.SHORT
    assert Direction.SHORT.opposite() == Direction.LONG


def test_direction_to_order_side():
    """Test Direction.to_order_side() conversion."""
    assert Direction.LONG.to_order_side() == "BUY"
    assert Direction.SHORT.to_order_side() == "SELL"


def test_direction_to_order_side_returns_string():
    """Test that to_order_side() returns a plain string, not an enum."""
    result = Direction.LONG.to_order_side()
    assert isinstance(result, str)
    assert result == "BUY"

    result = Direction.SHORT.to_order_side()
    assert isinstance(result, str)
    assert result == "SELL"

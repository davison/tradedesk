"""Tests for candle aggregation."""

import pytest

from tradedesk.marketdata import Candle
from tradedesk.aggregation import CandleAggregator, choose_base_period


def test_aggregates_three_5min_into_one_15min() -> None:
    """Test aggregating three 5-minute candles into one 15-minute candle."""
    agg = CandleAggregator(target_period="15MINUTE", base_period="5MINUTE")
    # factor
    assert agg.describe()[2] == 3

    instrument = "EURUSD"

    # Use aligned timestamps starting at 00:15:00 to ensure all 3 base candles fall in same bucket
    # Bucket [00:15:00, 00:30:00) contains candles at 00:20:00, 00:25:00, 00:29:00
    # Next candle at 00:30:00 triggers emission
    base_ts = 1767225600000
    c1 = Candle(timestamp=base_ts + 20*60*1000, open=100, high=105, low=99, close=104, volume=10, tick_count=1)
    c2 = Candle(timestamp=base_ts + 25*60*1000, open=104, high=106, low=103, close=105, volume=20, tick_count=2)
    c3 = Candle(timestamp=base_ts + 29*60*1000, open=105, high=108, low=104, close=107, volume=30, tick_count=3)
    c4 = Candle(timestamp=base_ts + 35*60*1000, open=107, high=109, low=106, close=108, volume=40, tick_count=4)

    assert agg.update(instrument=instrument, candle=c1) is None
    assert agg.update(instrument=instrument, candle=c2) is None
    assert agg.update(instrument=instrument, candle=c3) is None

    # c4 triggers emission of the 15-min bucket containing c1, c2, c3
    out = agg.update(instrument=instrument, candle=c4)
    assert out is not None

    # Emitted timestamp should be the end of the bucket (00:30:00)
    assert out.timestamp == str(base_ts + 30*60*1000)
    assert out.open == pytest.approx(100.0)
    assert out.high == pytest.approx(108.0)
    assert out.low == pytest.approx(99.0)
    assert out.close == pytest.approx(107.0)
    assert out.volume == pytest.approx(60.0)
    assert out.tick_count == 6


def test_state_is_independent_per_instrument() -> None:
    """Test that aggregation state is independent per instrument."""
    agg = CandleAggregator(target_period="10MINUTE", base_period="5MINUTE")
    # factor
    assert agg.describe()[2] == 2

    inst_a = "EURUSD"
    inst_b = "GBPUSD"

    # Use aligned timestamps: bucket [00:10:00, 00:20:00) contains candles at 00:12:00 and 00:17:00
    # Next candle at 00:22:00 triggers emission
    base_ts = 1767225600000  # 2026-01-01 00:00:00 UTC
    a1 = Candle(timestamp=base_ts + 12*60*1000, open=1, high=2, low=0.5, close=1.5)
    b1 = Candle(timestamp=base_ts + 12*60*1000, open=10, high=11, low=9, close=10.5)
    a2 = Candle(timestamp=base_ts + 17*60*1000, open=1.5, high=3, low=1.4, close=2.5)
    b2 = Candle(timestamp=base_ts + 17*60*1000, open=10.5, high=12, low=10, close=11.5)
    a3 = Candle(timestamp=base_ts + 22*60*1000, open=2.5, high=4, low=2.0, close=3.0)
    b3 = Candle(timestamp=base_ts + 22*60*1000, open=11.5, high=13, low=11, close=12.0)

    assert agg.update(instrument=inst_a, candle=a1) is None
    assert agg.update(instrument=inst_b, candle=b1) is None
    assert agg.update(instrument=inst_a, candle=a2) is None
    assert agg.update(instrument=inst_b, candle=b2) is None

    # a3 and b3 trigger emission of the 10-min buckets containing a1+a2 and b1+b2
    out_a = agg.update(instrument=inst_a, candle=a3)
    assert out_a is not None
    assert out_a.open == pytest.approx(1.0)
    assert out_a.close == pytest.approx(2.5)

    out_b = agg.update(instrument=inst_b, candle=b3)
    assert out_b is not None
    assert out_b.open == pytest.approx(10.0)
    assert out_b.close == pytest.approx(11.5)


def test_choose_base_period_prefers_5minute_when_divisible() -> None:
    """Test that choose_base_period prefers 5MINUTE for periods divisible by 5."""
    assert choose_base_period("15MINUTE") == "5MINUTE"
    assert choose_base_period("10MINUTE") == "5MINUTE"
    assert choose_base_period("30MINUTE") == "5MINUTE"


def test_choose_base_period_hour_passthrough() -> None:
    """Test that HOUR period is passed through unchanged."""
    assert choose_base_period("HOUR") == "HOUR"


def test_choose_base_period_falls_back_to_1minute_when_not_divisible_by_5() -> None:
    """Test that choose_base_period falls back to 1MINUTE for periods not divisible by 5."""
    assert choose_base_period("7MINUTE") == "1MINUTE"
    assert choose_base_period("13MINUTE") == "1MINUTE"

import numpy as np

from tradedesk.marketdata import ChartHistory


class TestChartHistory:
    def test_add_candle_respects_max_length(self, candle_factory):
        hist = ChartHistory("EPIC", "1MINUTE", max_length=3)

        for i in range(5):
            hist.add_candle(candle_factory(i))

        assert len(hist) == 3
        candles = hist.get_candles()
        # Should retain the last 3 candles: i=2,3,4
        assert candles[0].timestamp.endswith("02:00Z")
        assert candles[-1].timestamp.endswith("04:00Z")

    def test_get_candles_count_returns_most_recent_oldest_first(self, candle_factory):
        hist = ChartHistory("EPIC", "1MINUTE", max_length=10)
        for i in range(5):
            hist.add_candle(candle_factory(i))

        last_two = hist.get_candles(count=2)
        assert len(last_two) == 2
        assert last_two[0].timestamp.endswith("03:00Z")
        assert last_two[1].timestamp.endswith("04:00Z")

    def test_array_getters_return_expected_dtypes(self, candle_factory):
        hist = ChartHistory("EPIC", "1MINUTE", max_length=10)
        for i in range(3):
            hist.add_candle(candle_factory(i))

        assert hist.get_opens().dtype == np.float64
        assert hist.get_highs().dtype == np.float64
        assert hist.get_lows().dtype == np.float64
        assert hist.get_closes().dtype == np.float64
        assert hist.get_volumes().dtype == np.float64
        assert hist.get_tick_counts().dtype == np.int64
        assert hist.get_typical_prices().dtype == np.float64

        assert hist.get_closes().shape == (3,)
        assert hist.get_closes(count=2).shape == (2,)

    def test_latest_and_repr(self, candle_factory):
        hist = ChartHistory("EPIC", "1MINUTE", max_length=10)
        assert hist.latest is None

        c0 = candle_factory(0)
        hist.add_candle(c0)
        assert hist.latest == c0

        r = repr(hist)
        assert "ChartHistory(" in r
        assert "EPIC" in r
        assert "1MINUTE" in r

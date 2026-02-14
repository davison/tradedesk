"""Backtesting provider implementation."""

from .client import BacktestClient
from .excursions import CandleIndex, Excursions, build_candle_index, compute_excursions
from .harness import BacktestSpec, run_backtest
from .observers import BacktestRecorder, ProgressLogger, TrackerSync
from .streamer import BacktestStreamer, CandleSeries, MarketSeries

__all__ = [
    "BacktestClient",
    "BacktestRecorder",
    "BacktestSpec",
    "BacktestStreamer",
    "CandleIndex",
    "CandleSeries",
    "Excursions",
    "MarketSeries",
    "ProgressLogger",
    "TrackerSync",
    "build_candle_index",
    "compute_excursions",
    "run_backtest",
]

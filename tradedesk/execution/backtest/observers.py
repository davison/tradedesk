"""Backtest observers – collaborators extracted from the orchestrator.

Each class handles a single concern that was previously inline in
``PortfolioOrchestrator``.  They are designed as thin, stateful objects
that the orchestrator delegates to on each candle close.
"""

from __future__ import annotations

import logging

from tradedesk.execution.backtest.reporting import compute_equity
from tradedesk.recording import round_trips_from_fills
from tradedesk.recording.ledger import TradeLedger, trade_rows_from_trades
from tradedesk.recording.types import EquityRecord
from tradedesk.time_utils import candle_with_iso_timestamp, parse_timestamp

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


class BacktestRecorder:
    """Records opportunity snapshots and equity samples during a backtest."""

    def __init__(self, ledger: TradeLedger) -> None:
        self._ledger = ledger

    def record_snapshots(self, instrument: str, candle, *, strategies: dict) -> None:
        """Record per-instrument regime activity and portfolio-level k_active."""
        ts = candle_with_iso_timestamp(candle).timestamp

        s = strategies.get(instrument) or strategies.get(
            # PortfolioRunner keys by Instrument; try both str and Instrument
            next((k for k in strategies if str(k) == instrument), None)
        )
        if s is not None:
            self._ledger.opportunity.on_instrument_bar(
                instrument=instrument,
                timestamp=ts,
                active=bool(s.is_regime_active()),
            )

        k_active = sum(1 for st in strategies.values() if st.is_regime_active())
        self._ledger.opportunity.on_portfolio_snapshot(timestamp=ts, k_active=k_active)

    def sample_equity(self, candle, client) -> None:
        """Sample current equity from the backtest client into the ledger."""
        inner = getattr(client, "_inner", None)
        if inner is None:
            return
        eq = compute_equity(inner)
        ts = candle_with_iso_timestamp(candle).timestamp
        self._ledger.record_equity(EquityRecord(timestamp=ts, equity=float(eq)))


# ---------------------------------------------------------------------------
# Progress logging
# ---------------------------------------------------------------------------


class ProgressLogger:
    """Logs a message at the start of each new ISO week during a backtest."""

    def __init__(self) -> None:
        self._last_logged_week: tuple[int, int] | None = None

    def on_candle(self, candle) -> None:
        dt = parse_timestamp(candle.timestamp)
        year_week = (dt.year, dt.isocalendar()[1])
        if self._last_logged_week != year_week:
            log.info(
                "Backtest progress: Week %d/%d (%s)",
                year_week[1],
                year_week[0],
                dt.strftime("%Y-%m-%d"),
            )
            self._last_logged_week = year_week


# ---------------------------------------------------------------------------
# Policy tracker synchronisation
# ---------------------------------------------------------------------------


class TrackerSync:
    """Incrementally syncs completed round-trips to the policy tracker."""

    def __init__(self, ledger: TradeLedger, policy) -> None:
        self._ledger = ledger
        self._policy = policy
        self._last_extracted_trade_count: int = 0
        self._all_round_trips: list = []

    def sync(self) -> None:
        """Push new round-trips (if any) into the policy's tracker."""
        tracker = getattr(self._policy, "tracker", None)
        if tracker is None:
            return

        current_count = len(self._ledger.trades)
        if current_count < self._last_extracted_trade_count + 10:
            return

        all_rows = trade_rows_from_trades(self._ledger.trades)
        all_rts = round_trips_from_fills(all_rows)

        new_rts = all_rts[len(self._all_round_trips) :]
        self._all_round_trips = all_rts
        self._last_extracted_trade_count = current_count

        if not new_rts:
            return

        trades = []
        for rt in new_rts:
            entry_dt = parse_timestamp(rt.entry_ts)
            exit_dt = parse_timestamp(rt.exit_ts)
            trades.append(
                {
                    "instrument": rt.instrument,
                    "pnl": float(rt.pnl),
                    "entry_ts": rt.entry_ts,
                    "exit_ts": rt.exit_ts,
                    "hold_minutes": (exit_dt - entry_dt).total_seconds() / 60.0,
                }
            )

        tracker.update_from_trades(trades)
        log.debug(
            "Updated tracker with %d new round trips (total: %d)",
            len(trades),
            len(all_rts),
        )

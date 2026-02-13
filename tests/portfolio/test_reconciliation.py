"""Tests for tradedesk.portfolio.reconciliation."""

import pytest

from tradedesk.execution.broker import BrokerPosition
from tradedesk.portfolio.reconciliation import (
    DiscrepancyType,
    ReconciliationResult,
    _direction_matches,
    reconcile,
)
from tradedesk.recording.journal import JournalEntry


def _journal_entry(instrument="USDJPY", direction="long", size=1.0):
    return JournalEntry(
        instrument=instrument,
        direction=direction,
        size=size,
        entry_price=150.0,
        bars_held=5,
        mfe_points=2.0,
        entry_atr=0.8,
        updated_at="2025-01-15T12:00:00Z",
    )


def _broker_pos(instrument="USDJPY", direction="BUY", size=1.0):
    return BrokerPosition(
        instrument=instrument,
        direction=direction,
        size=size,
        entry_price=150.0,
        deal_id="DEAL123",
    )


class TestDirectionMatches:

    def test_long_buy(self):
        assert _direction_matches("long", "BUY") is True

    def test_short_sell(self):
        assert _direction_matches("short", "SELL") is True

    def test_long_sell(self):
        assert _direction_matches("long", "SELL") is False

    def test_none_direction(self):
        assert _direction_matches(None, "BUY") is False


class TestReconcile:

    def test_both_flat(self):
        result = reconcile(
            journal_positions={"USDJPY": _journal_entry(direction=None)},
            broker_positions=[],
            managed_instruments={"USDJPY"},
        )
        assert result.is_clean
        assert len(result.entries) == 1
        assert result.entries[0].discrepancy == DiscrepancyType.MATCHED

    def test_matched_positions(self):
        result = reconcile(
            journal_positions={"USDJPY": _journal_entry(direction="long", size=1.0)},
            broker_positions=[_broker_pos(direction="BUY", size=1.0)],
            managed_instruments={"USDJPY"},
        )
        assert result.is_clean

    def test_direction_mismatch(self):
        result = reconcile(
            journal_positions={"USDJPY": _journal_entry(direction="long")},
            broker_positions=[_broker_pos(direction="SELL")],
            managed_instruments={"USDJPY"},
        )
        assert not result.is_clean
        assert result.entries[0].discrepancy == DiscrepancyType.DIRECTION_MISMATCH

    def test_size_mismatch(self):
        result = reconcile(
            journal_positions={"USDJPY": _journal_entry(direction="long", size=1.0)},
            broker_positions=[_broker_pos(direction="BUY", size=2.0)],
            managed_instruments={"USDJPY"},
        )
        assert not result.is_clean
        assert result.entries[0].discrepancy == DiscrepancyType.SIZE_MISMATCH

    def test_orphan_broker_position(self):
        result = reconcile(
            journal_positions={},
            broker_positions=[_broker_pos(instrument="USDJPY")],
            managed_instruments={"USDJPY"},
        )
        assert not result.is_clean
        orphans = result.orphan_broker_positions
        assert len(orphans) == 1
        assert orphans[0].instrument == "USDJPY"

    def test_phantom_local_position(self):
        result = reconcile(
            journal_positions={"USDJPY": _journal_entry(direction="long")},
            broker_positions=[],
            managed_instruments={"USDJPY"},
        )
        assert not result.is_clean
        phantoms = result.phantom_local_positions
        assert len(phantoms) == 1
        assert phantoms[0].instrument == "USDJPY"

    def test_failed_exit(self):
        """Journal says flat (direction=None) but broker still has the position."""
        result = reconcile(
            journal_positions={"USDJPY": _journal_entry(direction=None)},
            broker_positions=[_broker_pos(instrument="USDJPY")],
            managed_instruments={"USDJPY"},
        )
        assert result.has_emergencies
        assert result.entries[0].discrepancy == DiscrepancyType.FAILED_EXIT

    def test_unmanaged_instrument_ignored(self):
        """Broker positions for unmanaged instruments should be ignored."""
        result = reconcile(
            journal_positions={},
            broker_positions=[_broker_pos(instrument="UNMANAGED")],
            managed_instruments={"USDJPY"},
        )
        assert result.is_clean

    def test_multiple_instruments(self):
        result = reconcile(
            journal_positions={
                "USDJPY": _journal_entry(instrument="USDJPY", direction="long", size=1.0),
                "GBPUSD": _journal_entry(instrument="GBPUSD", direction="short", size=2.0),
            },
            broker_positions=[
                _broker_pos(instrument="USDJPY", direction="BUY", size=1.0),
                _broker_pos(instrument="GBPUSD", direction="SELL", size=2.0),
            ],
            managed_instruments={"USDJPY", "GBPUSD"},
        )
        assert result.is_clean


class TestReconciliationResult:

    def test_is_clean(self):
        from tradedesk.portfolio.reconciliation import ReconciliationEntry
        result = ReconciliationResult(entries=[
            ReconciliationEntry(instrument="X", discrepancy=DiscrepancyType.MATCHED),
        ])
        assert result.is_clean

    def test_has_emergencies(self):
        from tradedesk.portfolio.reconciliation import ReconciliationEntry
        result = ReconciliationResult(entries=[
            ReconciliationEntry(instrument="X", discrepancy=DiscrepancyType.FAILED_EXIT),
        ])
        assert result.has_emergencies

    def test_orphan_broker_positions(self):
        from tradedesk.portfolio.reconciliation import ReconciliationEntry
        result = ReconciliationResult(entries=[
            ReconciliationEntry(instrument="X", discrepancy=DiscrepancyType.ORPHAN_BROKER),
            ReconciliationEntry(instrument="Y", discrepancy=DiscrepancyType.MATCHED),
        ])
        assert len(result.orphan_broker_positions) == 1

    def test_phantom_local_positions(self):
        from tradedesk.portfolio.reconciliation import ReconciliationEntry
        result = ReconciliationResult(entries=[
            ReconciliationEntry(instrument="X", discrepancy=DiscrepancyType.PHANTOM_LOCAL),
        ])
        assert len(result.phantom_local_positions) == 1

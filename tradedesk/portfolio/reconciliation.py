"""Position reconciliation between local journal and broker state."""

import logging
from dataclasses import dataclass
from enum import Enum

from tradedesk.execution import BrokerPosition
from tradedesk.recording.journal import JournalEntry

log = logging.getLogger(__name__)


class DiscrepancyType(Enum):
    """Classification of journal-vs-broker mismatches."""

    MATCHED = "matched"
    ORPHAN_BROKER = "orphan_broker"  # broker has position, journal does not
    PHANTOM_LOCAL = "phantom_local"  # journal has position, broker does not
    SIZE_MISMATCH = "size_mismatch"  # both have it, sizes differ
    DIRECTION_MISMATCH = "direction_mismatch"  # both have it, directions differ
    FAILED_EXIT = "failed_exit"  # journal says flat, broker still has position


@dataclass(frozen=True)
class ReconciliationEntry:
    """Result of comparing a single instrument."""

    instrument: str
    discrepancy: DiscrepancyType
    journal_direction: str | None = None
    journal_size: float | None = None
    broker_direction: str | None = None
    broker_size: float | None = None
    broker_deal_id: str | None = None
    message: str = ""


@dataclass
class ReconciliationResult:
    """Complete result of reconciliation across all instruments."""

    entries: list[ReconciliationEntry]

    @property
    def is_clean(self) -> bool:
        return all(e.discrepancy == DiscrepancyType.MATCHED for e in self.entries)

    @property
    def has_emergencies(self) -> bool:
        return any(e.discrepancy == DiscrepancyType.FAILED_EXIT for e in self.entries)

    @property
    def orphan_broker_positions(self) -> list[ReconciliationEntry]:
        return [e for e in self.entries if e.discrepancy == DiscrepancyType.ORPHAN_BROKER]

    @property
    def phantom_local_positions(self) -> list[ReconciliationEntry]:
        return [e for e in self.entries if e.discrepancy == DiscrepancyType.PHANTOM_LOCAL]


def _direction_matches(journal_dir: str | None, broker_dir: str) -> bool:
    """Compare journal direction (long/short) to broker direction (BUY/SELL)."""
    if journal_dir is None:
        return False
    mapping = {"long": "BUY", "short": "SELL"}
    return mapping.get(journal_dir, "") == broker_dir


def reconcile(
    *,
    journal_positions: dict[str, JournalEntry],
    broker_positions: list[BrokerPosition],
    managed_instruments: set[str],
) -> ReconciliationResult:
    """
    Compare local journal state against broker positions.

    Args:
        journal_positions: Position state from the on-disk journal, keyed by
            instrument.  Entries with ``direction=None`` represent flat (no position).
        broker_positions: Live positions from ``GET /positions``.
        managed_instruments: The set of instruments this portfolio instance manages.
            Broker positions for instruments NOT in this set are ignored (they may
            belong to manual trades or a different portfolio).

    Returns:
        A :class:`ReconciliationResult` with per-instrument entries.
    """
    entries: list[ReconciliationEntry] = []

    # Index broker positions by instrument (only managed ones)
    broker_by_instrument: dict[str, BrokerPosition] = {}
    for bp in broker_positions:
        if bp.instrument in managed_instruments:
            broker_by_instrument[bp.instrument] = bp

    all_instruments = managed_instruments | set(broker_by_instrument.keys())

    for instrument in sorted(all_instruments):
        journal_entry = journal_positions.get(instrument)
        broker_pos = broker_by_instrument.get(instrument)

        journal_has_position = (
            journal_entry is not None and journal_entry.direction is not None
        )
        broker_has_position = broker_pos is not None

        if not journal_has_position and not broker_has_position:
            # Both flat
            entries.append(ReconciliationEntry(
                instrument=instrument,
                discrepancy=DiscrepancyType.MATCHED,
            ))

        elif journal_has_position and broker_has_position:
            assert journal_entry is not None and broker_pos is not None
            # Both have a position -- check details
            if not _direction_matches(journal_entry.direction, broker_pos.direction):
                entries.append(ReconciliationEntry(
                    instrument=instrument,
                    discrepancy=DiscrepancyType.DIRECTION_MISMATCH,
                    journal_direction=journal_entry.direction,
                    journal_size=journal_entry.size,
                    broker_direction=broker_pos.direction,
                    broker_size=broker_pos.size,
                    broker_deal_id=broker_pos.deal_id,
                    message=(
                        f"Direction mismatch: journal={journal_entry.direction} "
                        f"broker={broker_pos.direction}"
                    ),
                ))
            elif abs((journal_entry.size or 0) - broker_pos.size) > 1e-6:
                entries.append(ReconciliationEntry(
                    instrument=instrument,
                    discrepancy=DiscrepancyType.SIZE_MISMATCH,
                    journal_direction=journal_entry.direction,
                    journal_size=journal_entry.size,
                    broker_direction=broker_pos.direction,
                    broker_size=broker_pos.size,
                    broker_deal_id=broker_pos.deal_id,
                    message=(
                        f"Size mismatch: journal={journal_entry.size} "
                        f"broker={broker_pos.size}"
                    ),
                ))
            else:
                entries.append(ReconciliationEntry(
                    instrument=instrument,
                    discrepancy=DiscrepancyType.MATCHED,
                    journal_direction=journal_entry.direction,
                    journal_size=journal_entry.size,
                    broker_direction=broker_pos.direction,
                    broker_size=broker_pos.size,
                    broker_deal_id=broker_pos.deal_id,
                ))

        elif not journal_has_position and broker_has_position:
            assert broker_pos is not None
            # Journal says flat but broker has position.
            # If journal entry exists with direction=None, we TRIED to close
            # but broker still has it => FAILED_EXIT.
            if journal_entry is not None and journal_entry.direction is None:
                entries.append(ReconciliationEntry(
                    instrument=instrument,
                    discrepancy=DiscrepancyType.FAILED_EXIT,
                    broker_direction=broker_pos.direction,
                    broker_size=broker_pos.size,
                    broker_deal_id=broker_pos.deal_id,
                    message=(
                        "EMERGENCY: Journal records flat but broker has position "
                        "(failed exit?)"
                    ),
                ))
            else:
                entries.append(ReconciliationEntry(
                    instrument=instrument,
                    discrepancy=DiscrepancyType.ORPHAN_BROKER,
                    broker_direction=broker_pos.direction,
                    broker_size=broker_pos.size,
                    broker_deal_id=broker_pos.deal_id,
                    message="Broker has position not tracked in journal",
                ))

        else:
            # journal_has_position and not broker_has_position
            assert journal_entry is not None
            entries.append(ReconciliationEntry(
                instrument=instrument,
                discrepancy=DiscrepancyType.PHANTOM_LOCAL,
                journal_direction=journal_entry.direction,
                journal_size=journal_entry.size,
                message=(
                    "Journal has position but broker does not "
                    "(was it closed externally?)"
                ),
            ))

    return ReconciliationResult(entries=entries)

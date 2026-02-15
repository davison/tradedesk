"""Centralised timestamp handling.

All timestamp parsing and conversion goes through this module.
Internal representation: UTC-aware ``datetime``.
Milliseconds-since-epoch used only at I/O boundaries (IG API, CandleAggregator).
"""

from dataclasses import replace
from datetime import datetime, timezone

from tradedesk.marketdata import Candle


# ---------------------------------------------------------------------------
# Core conversions
# ---------------------------------------------------------------------------


def parse_timestamp(ts: str | int | float) -> datetime:
    """Parse any timestamp representation to a UTC-aware datetime.

    Accepted inputs:
      * ISO 8601 string (``T`` or space separator, with or without ``Z``)
      * ``YYYY/MM/DD`` date prefix (normalised to dashes)
      * Integer or float milliseconds since epoch
      * String containing a numeric value (e.g. ``"1640995200000"``)
      * Empty / whitespace-only string → ``datetime.now(UTC)``
        (defensive fallback kept for broker-mode edge cases)
    """
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

    s = (ts or "").strip()
    if not s:
        return datetime.now(timezone.utc)

    # String that looks like a number → treat as milliseconds
    if s.replace(".", "", 1).lstrip("-").isdigit():
        return datetime.fromtimestamp(int(float(s)) / 1000, tz=timezone.utc)

    # Normalise YYYY/MM/DD → YYYY-MM-DD
    if len(s) >= 10 and s[4] == "/" and s[7] == "/":
        s = f"{s[:4]}-{s[5:7]}-{s[8:]}"

    s = s.replace("Z", "+00:00")
    s = s.replace(" ", "T", 1)

    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def iso_to_ms(ts: str) -> int:
    """Convert an ISO timestamp string to milliseconds since epoch."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def ms_to_iso(ms: int) -> str:
    """Convert milliseconds since epoch to an ISO string.

    Uses space separator (``YYYY-MM-DD HH:MM:SS+00:00``) to match the CSV
    format used throughout the backtest pipeline.
    """
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.isoformat().replace("T", " ")


def now_utc_iso() -> str:
    """Current UTC time as an ISO string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Candle timestamp helpers
# ---------------------------------------------------------------------------


def candle_with_ms_timestamp(candle: Candle) -> Candle:
    """Return *candle* with its timestamp normalised to int milliseconds.

    Used at the boundary with :class:`CandleAggregator` which expects
    millisecond-int timestamps (IG streaming format).
    """
    ts = candle.timestamp
    if isinstance(ts, (int, float)):
        return replace(candle, timestamp=int(ts))
    return replace(candle, timestamp=iso_to_ms(str(ts)))  # type: ignore[arg-type]


def candle_with_iso_timestamp(candle: Candle) -> Candle:
    """Return *candle* with its timestamp normalised to an ISO string.

    Strategies and recording always work with ISO strings; this converts
    back from milliseconds when needed (e.g. after aggregation).
    """
    ts = candle.timestamp
    if isinstance(ts, str):
        if ts.replace(".", "", 1).lstrip("-").isdigit():
            return replace(candle, timestamp=ms_to_iso(int(float(ts))))
        return candle  # already ISO
    if isinstance(ts, int):
        return replace(candle, timestamp=ms_to_iso(ts))
    # Unexpected type – best-effort
    return replace(candle, timestamp=ms_to_iso(int(ts)))

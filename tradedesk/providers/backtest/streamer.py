from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from tradedesk.chartdata import Candle
from tradedesk.providers.base import Streamer
from tradedesk.providers.events import CandleClose

log = logging.getLogger(__name__)


def _parse_ts(ts: str) -> datetime:
    # Candle timestamps should be ISO-8601; allow a trailing 'Z'
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


@dataclass(frozen=True)
class CandleSeries:
    epic: str
    period: str
    candles: list[Candle]


class BacktestStreamer(Streamer):
    """
    Candle replay streamer.

    Replays completed candles (CandleClose events) in timestamp order across all
    series, calling `strategy._handle_event(...)`.
    """

    def __init__(self, client, series: Iterable[CandleSeries]):
        self._client = client
        self._series = list(series)
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def run(self, strategy) -> None:
        await self.connect()

        # Flatten to a single chronological stream.
        stream: list[tuple[datetime, str, str, Candle]] = []
        for s in self._series:
            for c in s.candles:
                stream.append((_parse_ts(c.timestamp), s.epic, s.period, c))

        stream.sort(key=lambda x: x[0])

        try:
            for _, epic, period, candle in stream:
                # Update client mark price (used for order fills)
                self._client._set_mark_price(epic, candle.close)  # internal, backtest-only
                event = CandleClose(epic=epic, period=period, candle=candle)
                await strategy._handle_event(event)
        finally:
            await self.disconnect()

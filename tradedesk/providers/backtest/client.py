from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

from tradedesk.chartdata import Candle
from tradedesk.providers.base import Client
from tradedesk.providers.backtest.streamer import BacktestStreamer, CandleSeries


@dataclass
class Trade:
    epic: str
    direction: str  # "BUY" or "SELL"
    size: float
    price: float
    timestamp: str | None = None


@dataclass
class Position:
    epic: str
    direction: str  # "LONG" or "SHORT"
    size: float
    entry_price: float


class BacktestClient(Client):
    """
    Backtesting client.

    - start/close are no-ops
    - get_historical_candles serves from in-memory history
    - get_streamer replays CandleClose events
    - place_market_order executes virtual market fills at the latest mark price
    """

    _deal_counter = itertools.count(1)

    def __init__(self, series: list[CandleSeries]):
        self._series = series
        self._history: dict[tuple[str, str], list[Candle]] = {
            (s.epic, s.period): list(s.candles) for s in series
        }

        self._started = False
        self._closed = False

        self._mark_price: dict[str, float] = {}
        self.trades: list[Trade] = []
        self.positions: dict[str, Position] = {}
        self.realised_pnl: float = 0.0

    @classmethod
    def from_history(cls, history: dict[tuple[str, str], list[Candle]]) -> "BacktestClient":
        series: list[CandleSeries] = []
        for (epic, period), candles in history.items():
            series.append(CandleSeries(epic=epic, period=period, candles=list(candles)))
        return cls(series)

    async def start(self) -> None:
        self._started = True

    async def close(self) -> None:
        self._closed = True

    def get_streamer(self):
        return BacktestStreamer(self, self._series)

    def _set_mark_price(self, epic: str, price: float) -> None:
        self._mark_price[epic] = float(price)

    def _get_mark_price(self, epic: str) -> float:
        if epic not in self._mark_price:
            raise RuntimeError(f"No mark price available for {epic} (no data replayed yet)")
        return self._mark_price[epic]

    async def get_market_snapshot(self, epic: str) -> dict[str, Any]:
        price = self._get_mark_price(epic)
        # Backtest uses mid-price; bid/offer equal for now.
        return {"snapshot": {"bid": price, "offer": price}}

    async def get_historical_candles(self, epic: str, period: str, num_points: int) -> list[Candle]:
        if num_points <= 0:
            return []
        candles = self._history.get((epic, period), [])
        return candles[-num_points:]

    async def place_market_order(
        self,
        epic: str,
        direction: str,
        size: float,
        currency: str = "USD",
        force_open: bool = True,
    ) -> dict[str, Any]:
        if not self._started:
            raise RuntimeError("BacktestClient not started")

        if size <= 0:
            raise ValueError("size must be > 0")

        direction = direction.upper()
        if direction not in {"BUY", "SELL"}:
            raise ValueError("direction must be BUY or SELL")

        price = self._get_mark_price(epic)
        self.trades.append(Trade(epic=epic, direction=direction, size=float(size), price=price))

        # Very simple netting model:
        # - BUY opens/increases LONG, SELL opens/increases SHORT
        # - If opposite direction order arrives, close the entire position if sizes match.
        pos = self.positions.get(epic)

        if pos is None:
            self.positions[epic] = Position(
                epic=epic,
                direction="LONG" if direction == "BUY" else "SHORT",
                size=float(size),
                entry_price=price,
            )
        else:
            same = (pos.direction == "LONG" and direction == "BUY") or (pos.direction == "SHORT" and direction == "SELL")
            if same:
                # Increase position: weighted avg entry
                new_size = pos.size + float(size)
                pos.entry_price = (pos.entry_price * pos.size + price * float(size)) / new_size
                pos.size = new_size
            else:
                # Opposite direction: close (only supports full close or reduce; compute realised on reduced amount)
                close_size = min(pos.size, float(size))
                if pos.direction == "LONG":
                    self.realised_pnl += (price - pos.entry_price) * close_size
                else:
                    self.realised_pnl += (pos.entry_price - price) * close_size

                pos.size -= close_size
                if pos.size <= 0:
                    self.positions.pop(epic, None)
                # If order size > position size, open residual opposite position
                residual = float(size) - close_size
                if residual > 0:
                    self.positions[epic] = Position(
                        epic=epic,
                        direction="LONG" if direction == "BUY" else "SHORT",
                        size=residual,
                        entry_price=price,
                    )

        return {
            "dealReference": f"BACKTEST-{next(self._deal_counter)}",
            "status": "FILLED",
            "epic": epic,
            "direction": direction,
            "size": float(size),
            "price": price,
            "currency": currency,
        }

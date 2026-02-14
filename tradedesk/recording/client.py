from typing import Any

from .ledger import TradeLedger
from .types import TradeRecord
from tradedesk.time_utils import now_utc_iso


class RecordingClient:
    """
    Transparent client wrapper that records executions.

    - Delegates all attributes/methods to the wrapped client.
    - Intercepts place_market_order to append a TradeRecord to the ledger.

    This keeps recording client-agnostic and avoids touching tradedesk/backtest internals.
    """

    def __init__(self, inner: Any, *, ledger: TradeLedger):
        self._inner = inner
        self._ledger = ledger

    def __getattr__(self, name: str) -> Any:
        # Delegate everything else
        return getattr(self._inner, name)

    def _current_timestamp(self) -> str:
        # BacktestClient maintains this; broker clients may later expose something similar.
        ts = getattr(self._inner, "_current_timestamp", None)
        if isinstance(ts, str) and ts:
            return ts
        # If the inner client doesn't provide a timestamp, fall back to now (UTC).
        # Returning a valid ISO timestamp prevents downstream parsers from
        # raising on empty strings (e.g. datetime.fromisoformat('')).
        return now_utc_iso()

    async def place_market_order(
        self,
        instrument: str,
        direction: str,
        size: float,
        **kwargs,
    ) -> dict[str, Any]:
        resp = await self._inner.place_market_order(
            instrument=instrument, direction=direction, size=size, **kwargs
        )
        self._record_trade(
            instrument=instrument,
            direction=direction,
            size=size,
            price=resp.get("price", None),
            reason="market_order",
        )
        return resp

    async def place_market_order_confirmed(
        self,
        instrument: str,
        direction: str,
        size: float,
        **kwargs,
    ) -> dict[str, Any]:
        resp = await self._inner.place_market_order_confirmed(
            instrument=instrument, direction=direction, size=size, **kwargs
        )
        self._record_trade(
            instrument=instrument,
            direction=direction,
            size=size,
            price=resp.get("price", None),
            reason="market_order",
        )
        return resp

    def _record_trade(
        self,
        instrument: str,
        direction: str,
        size: float,
        price: float,
        reason: str,
    ) -> None:
        if price is None:
            # fallback to mark price if available
            get_mark = getattr(self._inner, "get_mark_price", None)
            price = (
                float(get_mark(instrument))
                if callable(get_mark) and get_mark(instrument) is not None
                else 0.0
            )

        ts = self._current_timestamp()
        self._ledger.record_trade(
            TradeRecord(
                timestamp=ts,
                instrument=instrument,
                direction=direction,
                size=float(size),
                price=float(price),
                reason=reason,
            )
        )

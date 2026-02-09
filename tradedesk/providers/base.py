"""
Provider-neutral interfaces.

The intent is to keep tradedesk strategies independent from any single broker.
At this stage the interfaces are intentionally small; we will extend them as
we encapsulate streaming and implement backtesting.
"""

import abc
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING
from tradedesk.marketdata import Candle

if TYPE_CHECKING:
    from tradedesk.strategy import BaseStrategy


__all__ = [
    "AccountBalance",
    "BrokerPosition",
    "Client",
    "DealNotAcceptedException",
    "Streamer",
]


@dataclass(frozen=True)
class BrokerPosition:
    """Provider-neutral representation of a position held at the broker."""

    instrument: str
    direction: str  # "BUY" or "SELL" (broker-native)
    size: float
    entry_price: float
    deal_id: str
    currency: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class AccountBalance:
    """Provider-neutral snapshot of account funds."""

    balance: float  # total account value
    deposit: float  # margin used
    available: float  # funds available for new positions
    profit_loss: float  # unrealised P&L
    currency: str = ""


class DealNotAcceptedException(Exception):
    """Raised when a deal is not accepted after placing a market order."""
    pass

class Streamer(abc.ABC):
    """Abstract base for a real-time (or replay) market data stream."""

    @abc.abstractmethod
    async def connect(self) -> None:
        """Establish the underlying connection (e.g. Lightstreamer, WebSocket)."""
        raise NotImplementedError

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Tear down the underlying connection and unsubscribe."""
        raise NotImplementedError

    @abc.abstractmethod
    async def run(self, strategy: "BaseStrategy") -> None:
        """Run the stream and dispatch events into the supplied strategy."""
        raise NotImplementedError


class Client(abc.ABC):
    """Abstract base for broker/provider clients."""

    @abc.abstractmethod
    async def start(self) -> None:
        """Initialise the client (e.g. create session, authenticate)."""
        raise NotImplementedError

    @abc.abstractmethod
    async def close(self) -> None:
        """Close any underlying resources."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_market_snapshot(self, instrument: str) -> dict[str, Any]:
        """
        Fetch a snapshot of the current market state for an instrument.

        Args:
            instrument: The instrument identifier.

        Returns:
            A dictionary containing the raw market snapshot data.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_historical_candles(
        self, instrument: str, period: str, num_points: int
    ) -> list[Candle]:
        """
        Fetch historical OHLCV candles.

        Args:
            instrument: The instrument identifier.
            period: The candle timeframe (e.g., "15MINUTE").
            num_points: The number of historical candles to retrieve.

        Returns:
            A list of `Candle` objects, ordered from oldest to newest.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def place_market_order(
        self,
        instrument: str,
        direction: str,
        size: float,
        currency: str = "USD",
        force_open: bool = True,
    ) -> dict[str, Any]:
        """Place a market order without requiring confirmation.

        This method should not block, the client is responsible for tracking order status.

        Args:
            instrument: The instrument identifier.
            direction: The direction of the trade ("BUY" or "SELL").
            size: The size of the position.
            currency: The currency code (default "USD").
            force_open: If True, opens a new position even if an opposing
                position exists (netting vs hedging).

        Returns:
            A dictionary containing the deal reference or order ID.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def place_market_order_confirmed(
        self,
        instrument: str,
        direction: str,
        size: float,
        currency: str = "USD",
        force_open: bool = True,
    ) -> dict[str, Any]:
        """Place a market order and confirm its execution.

        This method should block until the order is fully executed.

        Args:
            instrument: The instrument identifier.
            direction: The direction of the trade ("BUY" or "SELL").
            size: The size of the position.
            currency: The currency code (default "USD").
            force_open: If True, opens a new position even if an opposing
                position exists.

        Returns:
            A dictionary containing the full deal confirmation details.

        Raises:
            DealNotAcceptedException: If the order was rejected by the broker.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_positions(self) -> list[BrokerPosition]:
        """Fetch all open positions from the broker.

        Returns:
            A list of ``BrokerPosition`` objects representing every open
            position on the account.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_account_balance(self) -> AccountBalance:
        """Fetch current account balance and margin summary.

        Returns:
            An ``AccountBalance`` snapshot with balance, margin usage,
            available funds, and unrealised P&L.
        """
        raise NotImplementedError

    def get_streamer(self) -> Streamer:
        """Return a Streamer implementation for this client.

        Not wired in yet; will be introduced when we encapsulate Lightstreamer.
        """
        raise NotImplementedError

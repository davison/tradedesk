"""
Provider-agnostic interfaces.

This module defines the stable interfaces used by strategies and runners.
Concrete provider implementations (e.g. IG) should implement these contracts.
"""

from .broker import (
    AccountBalance,
    BrokerPosition,
    DealRejectedException,
    Direction,
)
from .client import Client
from .position import PositionTracker
from .streamer import Streamer

__all__ = [
    "AccountBalance",
    "BrokerPosition",
    "Client",
    "DealRejectedException",
    "Direction",
    "PositionTracker",
    "Streamer",
]

"""Abstract transport interfaces for future broker connections."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pi_rpc.transport.protocol import JsonObject


class BrokerConnection(ABC):
    """A client connection to a pi-rpc broker."""

    @abstractmethod
    async def send(self, message: JsonObject) -> None:
        """Send one protocol message."""

    @abstractmethod
    def receive(self) -> AsyncIterator[JsonObject]:
        """Yield protocol messages until the connection closes."""

    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""


class BrokerTransport(ABC):
    """Transport boundary for client-to-broker communication."""

    @abstractmethod
    async def connect(self) -> BrokerConnection:
        """Connect to a broker and return a connection."""

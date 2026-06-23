"""Unix-domain socket transport for pi-rpc brokers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from pi_rpc.transport.base import BrokerConnection, BrokerTransport
from pi_rpc.transport.protocol import JsonObject, decode_jsonl_line, encode_jsonl


class UnixBrokerConnection(BrokerConnection):
    """A JSONL connection over a Unix-domain socket."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def send(self, message: JsonObject) -> None:
        """Send one JSONL message."""

        self._writer.write(encode_jsonl(message))
        await self._writer.drain()

    async def _receive(self) -> AsyncIterator[JsonObject]:
        while line := await self._reader.readline():
            yield decode_jsonl_line(line)

    def receive(self) -> AsyncIterator[JsonObject]:
        """Yield JSONL messages from the broker."""

        return self._receive()

    async def close(self) -> None:
        """Close the Unix socket connection."""

        self._writer.close()
        await self._writer.wait_closed()


class UnixBrokerTransport(BrokerTransport):
    """Connect to a broker over a Unix-domain socket path."""

    def __init__(self, socket_path: str | Path) -> None:
        self.socket_path = Path(socket_path)

    async def connect(self) -> BrokerConnection:
        """Open a Unix-domain socket connection."""

        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
        return UnixBrokerConnection(reader, writer)

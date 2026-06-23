"""Client helpers for lifecycle requests to a broker."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from pi_rpc.paths import paths_for_session
from pi_rpc.transport.protocol import JsonObject
from pi_rpc.transport.unix import UnixBrokerTransport


class BrokerUnavailableError(ConnectionError):
    """Raised when a session broker cannot be reached."""


async def request_broker(session_id: str, message: JsonObject) -> dict[str, Any]:
    """Send one request to a session broker and return one response."""
    async for response in stream_broker(session_id, message):
        return response
    msg = "broker closed without a response"
    raise BrokerUnavailableError(msg)


async def stream_broker(session_id: str, message: JsonObject) -> AsyncIterator[dict[str, Any]]:
    """Send one request to a broker and yield all streamed responses."""
    paths = paths_for_session(session_id)
    transport = UnixBrokerTransport(paths.socket_path)
    try:
        connection = await transport.connect()
    except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
        raise BrokerUnavailableError(str(paths.socket_path)) from exc

    try:
        await connection.send(message)
        async for response in connection.receive():
            yield response
    finally:
        await connection.close()


def broker_socket_exists(session_id: str) -> bool:
    """Return whether the session socket path exists."""
    return Path(paths_for_session(session_id).socket_path).exists()

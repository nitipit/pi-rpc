from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from pi_rpc.broker.server import BrokerServer
from pi_rpc.paths import SessionPaths
from pi_rpc.transport.unix import UnixBrokerTransport


@pytest.mark.asyncio
async def test_broker_server_handles_status_and_shutdown(tmp_path: Path) -> None:
    paths = SessionPaths(
        session_id="test-session",
        file_stem="test-session-abc123",
        socket_path=tmp_path / "test.sock",
        pid_path=tmp_path / "test.pid",
        metadata_path=tmp_path / "test.json",
        log_path=tmp_path / "test.log",
    )
    server = BrokerServer(paths=paths, cwd=str(tmp_path), name="Test Session")
    server_task = asyncio.create_task(server.serve())

    try:
        transport = UnixBrokerTransport(paths.socket_path)
        for _ in range(100):
            if paths.socket_path.exists():
                break
            await asyncio.sleep(0.01)

        connection = await transport.connect()
        await connection.send({"type": "status"})
        responses = connection.receive()
        status = await anext(responses)
        await connection.close()

        assert status["type"] == "status"
        assert status["metadata"]["session_id"] == "test-session"
        assert status["metadata"]["name"] == "Test Session"

        connection = await transport.connect()
        await connection.send({"type": "shutdown"})
        shutdown = await anext(connection.receive())
        await connection.close()

        assert shutdown == {"type": "shutdown_ack", "session_id": "test-session"}
        await asyncio.wait_for(server_task, timeout=1)
        assert not paths.socket_path.exists()
        assert not paths.pid_path.exists()
    finally:
        if not server_task.done():
            server_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server_task

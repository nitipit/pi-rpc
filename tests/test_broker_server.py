from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from pi_rpc.broker.server import BrokerServer
from pi_rpc.paths import SessionPaths
from pi_rpc.transport.unix import UnixBrokerTransport


def write_fake_pi(tmp_path: Path) -> Path:
    script = tmp_path / "fake-pi"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "for line in sys.stdin:\n"
        "    payload = json.loads(line)\n"
        "    if payload.get('type') == 'get_state':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'get_state', 'success': True, 'data': {'sessionId': 'test-session'}}), flush=True)\n"
        "    else:\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': payload.get('type'), 'success': True}), flush=True)\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | 0o111)
    return script


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
    fake_pi = write_fake_pi(tmp_path)
    server = BrokerServer(paths=paths, cwd=str(tmp_path), name="Test Session", pi_bin=str(fake_pi))
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
        assert status["metadata"]["pi_ready"] is True
        assert isinstance(status["metadata"]["pi_pid"], int)
        assert status["pi"]["last_state"] == {"sessionId": "test-session"}

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

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


def write_fake_pi_with_prompt_events(tmp_path: Path) -> Path:
    script = tmp_path / "fake-pi-prompt"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "for line in sys.stdin:\n"
        "    payload = json.loads(line)\n"
        "    if payload.get('type') == 'get_state':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'get_state', 'success': True, 'data': {'sessionId': 'test-session'}}), flush=True)\n"
        "    elif payload.get('type') == 'prompt':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'prompt', 'success': True}), flush=True)\n"
        "        print(json.dumps({'type': 'agent_start'}), flush=True)\n"
        "        print(json.dumps({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_start', 'contentIndex': 0}}), flush=True)\n"
        "        print(json.dumps({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'contentIndex': 0, 'delta': 'Hello '}}), flush=True)\n"
        "        print(json.dumps({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'contentIndex': 0, 'delta': 'world'}}), flush=True)\n"
        "        print(json.dumps({'type': 'agent_end', 'messages': []}), flush=True)\n"
        "    else:\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': payload.get('type'), 'success': True}), flush=True)\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | 0o111)
    return script


def write_fake_pi_with_control_command_events(tmp_path: Path) -> Path:
    script = tmp_path / "fake-pi-control"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "for line in sys.stdin:\n"
        "    payload = json.loads(line)\n"
        "    if payload.get('type') == 'get_state':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'get_state', 'success': True, 'data': {'sessionId': 'test-session', 'status': 'running'}}), flush=True)\n"
        "    elif payload.get('type') == 'get_available_models':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'get_available_models', 'success': True, 'data': ['gpt-4', 'claude'] }), flush=True)\n"
        "    elif payload.get('type') == 'get_session_stats':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'get_session_stats', 'success': True, 'data': {'messages': 3, 'tools': 2}}), flush=True)\n"
        "    elif payload.get('type') == 'get_messages':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'get_messages', 'success': True, 'data': [{'role': 'user', 'content': 'hello'}, {'role': 'assistant', 'content': 'done'}]}), flush=True)\n"
        "    elif payload.get('type') == 'get_last_assistant_text':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'get_last_assistant_text', 'success': True, 'data': {'text': 'previous assistant output'}}), flush=True)\n"
        "    elif payload.get('type') == 'get_commands':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'get_commands', 'success': True, 'data': [{'name': 'echo', 'description': 'repeat input', 'source': 'builtin'}, {'name': 'run', 'description': 'run shell', 'source': 'plugin'}]}), flush=True)\n"
        "    elif payload.get('type') == 'set_model':\n"
        "        model = payload.get('model')\n"
        "        if isinstance(model, str):\n"
        "            print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'set_model', 'success': True, 'data': {'model': model}}), flush=True)\n"
        "        else:\n"
        "            print(json.dumps({'id': payload.get('id'), 'type': 'error', 'error': 'missing model'}), flush=True)\n"
        "    elif payload.get('type') == 'cycle_model':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'cycle_model', 'success': True, 'data': {'model': 'gpt-4'}}), flush=True)\n"
        "    elif payload.get('type') == 'set_thinking_level':\n"
        "        level = payload.get('level')\n"
        "        if isinstance(level, str):\n"
        "            print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'set_thinking_level', 'success': True, 'data': {'level': level}}), flush=True)\n"
        "        else:\n"
        "            print(json.dumps({'id': payload.get('id'), 'type': 'error', 'error': 'missing level'}), flush=True)\n"
        "    elif payload.get('type') == 'cycle_thinking_level':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'cycle_thinking_level', 'success': True, 'data': {'level': 'high'}}), flush=True)\n"
        "    elif payload.get('type') in ('steer', 'follow_up', 'abort'):\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': payload.get('type'), 'success': True}), flush=True)\n"
        "        print(json.dumps({'type': 'agent_end', 'messages': []}), flush=True)\n"
        "    elif payload.get('type') == 'prompt':\n"
        "        print(json.dumps({'id': payload.get('id'), 'type': 'response', 'command': 'prompt', 'success': True}), flush=True)\n"
        "        print(json.dumps({'type': 'agent_end', 'messages': []}), flush=True)\n"
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


@pytest.mark.asyncio
async def test_broker_server_streams_prompt_events_until_agent_end(tmp_path: Path) -> None:
    paths = SessionPaths(
        session_id="test-session",
        file_stem="test-session-abc123",
        socket_path=tmp_path / "test.sock",
        pid_path=tmp_path / "test.pid",
        metadata_path=tmp_path / "test.json",
        log_path=tmp_path / "test.log",
    )
    fake_pi = write_fake_pi_with_prompt_events(tmp_path)
    server = BrokerServer(paths=paths, cwd=str(tmp_path), name="Test Session", pi_bin=str(fake_pi))
    server_task = asyncio.create_task(server.serve())

    try:
        transport = UnixBrokerTransport(paths.socket_path)
        for _ in range(100):
            if paths.socket_path.exists():
                break
            await asyncio.sleep(0.01)

        connection = await transport.connect()
        await connection.send({"type": "prompt", "message": "Hello"})
        responses: list[dict[str, object]] = []
        async for response in connection.receive():
            responses.append(response)
            if response["type"] == "agent_end":
                break
        await connection.close()

        assert responses[0]["type"] == "response"
        assert responses[0]["command"] == "prompt"
        assert responses[0]["success"] is True
        assert any(r["type"] == "agent_end" for r in responses)
        assert any(
            r.get("type") == "message_update"
            and isinstance((assistant_event := r.get("assistantMessageEvent")), dict)
            and assistant_event.get("type") == "text_delta"
            for r in responses
        )

        shutdown_connection = await transport.connect()
        await shutdown_connection.send({"type": "shutdown"})
        await anext(shutdown_connection.receive())
        await shutdown_connection.close()

        await asyncio.wait_for(server_task, timeout=1)
    finally:
        if not server_task.done():
            server_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server_task


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command, payload",
    [
        ("steer", {"message": "reroute"}),
        ("follow_up", {"message": "then do this"}),
        ("abort", {}),
    ],
)
async def test_broker_server_forwards_control_commands_without_event_streaming(
    tmp_path: Path,
    command: str,
    payload: dict[str, str],
) -> None:
    paths = SessionPaths(
        session_id="test-session",
        file_stem="test-session-abc123",
        socket_path=tmp_path / "test.sock",
        pid_path=tmp_path / "test.pid",
        metadata_path=tmp_path / "test.json",
        log_path=tmp_path / "test.log",
    )
    fake_pi = write_fake_pi_with_control_command_events(tmp_path)
    server = BrokerServer(paths=paths, cwd=str(tmp_path), name="Test Session", pi_bin=str(fake_pi))
    server_task = asyncio.create_task(server.serve())

    try:
        transport = UnixBrokerTransport(paths.socket_path)
        for _ in range(100):
            if paths.socket_path.exists():
                break
            await asyncio.sleep(0.01)

        connection = await transport.connect()
        await connection.send({"type": command, **payload})
        responses: list[dict[str, object]] = []
        async for response in connection.receive():
            responses.append(response)
        await connection.close()

        assert len(responses) == 1
        assert responses[0]["type"] == "response"
        assert responses[0]["command"] == command
        assert responses[0]["success"] is True

        shutdown_connection = await transport.connect()
        await shutdown_connection.send({"type": "shutdown"})
        await anext(shutdown_connection.receive())
        await shutdown_connection.close()

        await asyncio.wait_for(server_task, timeout=1)
    finally:
        if not server_task.done():
            server_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server_task


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "broker_command, pi_command, data_key",
    [
        ("state", "get_state", "sessionId"),
        ("models", "get_available_models", "gpt-4"),
        ("stats", "get_session_stats", "messages"),
        ("messages", "get_messages", "role"),
        ("last-assistant-text", "get_last_assistant_text", "text"),
        ("commands", "get_commands", "name"),
    ],
)
async def test_broker_server_maps_read_only_commands_to_pi_commands(
    tmp_path: Path,
    broker_command: str,
    pi_command: str,
    data_key: str,
) -> None:
    paths = SessionPaths(
        session_id="test-session",
        file_stem="test-session-abc123",
        socket_path=tmp_path / "test.sock",
        pid_path=tmp_path / "test.pid",
        metadata_path=tmp_path / "test.json",
        log_path=tmp_path / "test.log",
    )
    fake_pi = write_fake_pi_with_control_command_events(tmp_path)
    server = BrokerServer(paths=paths, cwd=str(tmp_path), name="Test Session", pi_bin=str(fake_pi))
    server_task = asyncio.create_task(server.serve())

    try:
        transport = UnixBrokerTransport(paths.socket_path)
        for _ in range(100):
            if paths.socket_path.exists():
                break
            await asyncio.sleep(0.01)

        connection = await transport.connect()
        await connection.send({"type": broker_command})
        responses: list[dict[str, object]] = []
        async for response in connection.receive():
            responses.append(response)
        await connection.close()

        assert len(responses) == 1
        assert responses[0]["type"] == "response"
        assert responses[0]["command"] == pi_command
        assert responses[0]["success"] is True
        response_data = responses[0]["data"]
        if isinstance(response_data, dict):
            assert data_key in response_data
        elif isinstance(response_data, list):
            assert response_data
            first_item = response_data[0]
            if isinstance(first_item, dict):
                assert data_key in first_item
            else:
                assert data_key in response_data
        else:
            raise AssertionError("Expected list or dict data")

        shutdown_connection = await transport.connect()
        await shutdown_connection.send({"type": "shutdown"})
        await anext(shutdown_connection.receive())
        await shutdown_connection.close()

        await asyncio.wait_for(server_task, timeout=1)
    finally:
        if not server_task.done():
            server_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server_task


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "broker_request, pi_command, data_key",
    [
        ({"type": "model", "model": "gpt-4"}, "set_model", "model"),
        ({"type": "cycle-model"}, "cycle_model", "model"),
        ({"type": "thinking", "level": "high"}, "set_thinking_level", "level"),
        ({"type": "cycle-thinking"}, "cycle_thinking_level", "level"),
    ],
)
async def test_broker_server_maps_mutation_commands_to_pi_commands(
    tmp_path: Path,
    broker_request: dict[str, str],
    pi_command: str,
    data_key: str,
) -> None:
    paths = SessionPaths(
        session_id="test-session",
        file_stem="test-session-abc123",
        socket_path=tmp_path / "test.sock",
        pid_path=tmp_path / "test.pid",
        metadata_path=tmp_path / "test.json",
        log_path=tmp_path / "test.log",
    )
    fake_pi = write_fake_pi_with_control_command_events(tmp_path)
    server = BrokerServer(paths=paths, cwd=str(tmp_path), name="Test Session", pi_bin=str(fake_pi))
    server_task = asyncio.create_task(server.serve())

    try:
        transport = UnixBrokerTransport(paths.socket_path)
        for _ in range(100):
            if paths.socket_path.exists():
                break
            await asyncio.sleep(0.01)

        connection = await transport.connect()
        await connection.send(broker_request)
        responses: list[dict[str, object]] = []
        async for response in connection.receive():
            responses.append(response)
        await connection.close()

        assert len(responses) == 1
        assert responses[0]["type"] == "response"
        assert responses[0]["command"] == pi_command
        assert responses[0]["success"] is True
        response_data = responses[0]["data"]
        if not isinstance(response_data, dict):
            raise AssertionError("Expected dict data")
        assert data_key in response_data

        shutdown_connection = await transport.connect()
        await shutdown_connection.send({"type": "shutdown"})
        await anext(shutdown_connection.receive())
        await shutdown_connection.close()

        await asyncio.wait_for(server_task, timeout=1)
    finally:
        if not server_task.done():
            server_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server_task

"""Unix-socket broker lifecycle server for one pi-rpc session."""

from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from pathlib import Path

from pi_rpc.broker.metadata import BrokerMetadata, utc_now_iso, write_metadata
from pi_rpc.broker.pi_process import PiRpcProcess
from pi_rpc.broker.schemas import (
    PASS_THROUGH_REQUEST_TYPES,
    BrokerSchemaError,
    validate_broker_request,
)
from pi_rpc.paths import SessionPaths
from pi_rpc.transport.protocol import JsonObject, ProtocolError, decode_jsonl_line, encode_jsonl

_BROKER_TO_PI_COMMAND = {
    "state": "get_state",
    "models": "get_available_models",
    "stats": "get_session_stats",
    "messages": "get_messages",
    "last-assistant-text": "get_last_assistant_text",
    "commands": "get_commands",
    "bash": "bash",
    "abort_bash": "abort_bash",
    "model": "set_model",
    "cycle-model": "cycle_model",
    "thinking": "set_thinking_level",
    "cycle-thinking": "cycle_thinking_level",
    "name": "set_session_name",
    "compact": "compact",
    "auto-compaction": "set_auto_compaction",
    "auto-retry": "set_auto_retry",
    "steering-mode": "set_steering_mode",
    "follow-up-mode": "set_follow_up_mode",
    "abort-retry": "abort_retry",
    "new-session": "new_session",
    "switch-session": "switch_session",
    "clone": "clone",
    "fork": "fork",
    "fork-messages": "get_fork_messages",
    "export-html": "export_html",
}


class BrokerServer:
    """Small lifecycle broker for one session id.

    The broker owns one managed ``pi --mode rpc`` subprocess and exposes local
    lifecycle/status control over a Unix-domain socket.
    """

    def __init__(
        self,
        *,
        paths: SessionPaths,
        cwd: str,
        name: str | None = None,
        pi_bin: str = "pi",
    ) -> None:
        self.paths = paths
        self.cwd = cwd
        self.name = name
        self.pi_process = PiRpcProcess(
            session_id=paths.session_id,
            cwd=cwd,
            log_path=paths.log_path,
            pi_bin=pi_bin,
            name=name,
        )
        self.started_at = utc_now_iso()
        self._server: asyncio.AbstractServer | None = None
        self._shutdown_event = asyncio.Event()

    @property
    def metadata(self) -> BrokerMetadata:
        """Return current broker metadata."""
        return BrokerMetadata(
            session_id=self.paths.session_id,
            broker_pid=os.getpid(),
            pi_pid=self.pi_process.pid,
            socket_path=str(self.paths.socket_path),
            pid_path=str(self.paths.pid_path),
            metadata_path=str(self.paths.metadata_path),
            log_path=str(self.paths.log_path),
            cwd=self.cwd,
            name=self.name,
            started_at=self.started_at,
            pi_ready=self.pi_process.ready,
        )

    async def serve(self) -> None:
        """Run the broker until a shutdown request is received."""
        await self._prepare_paths()
        await self.pi_process.start()
        self._server = await asyncio.start_unix_server(
            self._handle_client, str(self.paths.socket_path)
        )
        self.paths.pid_path.write_text(str(os.getpid()), encoding="utf-8")
        write_metadata(self.metadata)

        async with self._server:
            await self._shutdown_event.wait()
            self._server.close()
            await self._server.wait_closed()
        await self.pi_process.stop()
        self._cleanup_runtime_files()

    async def _prepare_paths(self) -> None:
        self.paths.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self.paths.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        if self.paths.socket_path.exists():
            self.paths.socket_path.unlink()

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            while line := await reader.readline():
                try:
                    request = decode_jsonl_line(line)
                    request_type = validate_broker_request(request)
                    if request_type in PASS_THROUGH_REQUEST_TYPES:
                        await self._forward_command(
                            request, writer, stream=request_type == "prompt"
                        )
                        break
                    response = await self._dispatch(request, request_type)
                except (ProtocolError, BrokerSchemaError) as exc:
                    response = {"type": "error", "error": str(exc)}
                writer.write(encode_jsonl(response))
                await writer.drain()
                if response.get("type") == "shutdown_ack":
                    break
        finally:
            writer.close()
            await writer.wait_closed()

    async def _dispatch(self, request: JsonObject, request_type: str) -> JsonObject:
        handlers = {
            "ping": self._ping,
            "status": self._status,
            "shutdown": self._shutdown,
            "ui-response": self._extension_ui_response,
        }
        handler = handlers.get(request_type)
        if handler is None:
            return {"type": "error", "error": f"unsupported broker request: {request_type}"}
        return await handler(request)

    async def _forward_command(
        self,
        request: JsonObject,
        writer: asyncio.StreamWriter,
        *,
        stream: bool,
    ) -> None:
        queue = self.pi_process.subscribe_events() if stream else None
        forward_request = self._map_broker_to_pi_request(request)
        try:
            response = await self.pi_process.send_command(forward_request)
            writer.write(encode_jsonl(response))
            await writer.drain()

            if not stream or not self._should_stream_events(response):
                return

            while True:
                message = await queue.get() if queue is not None else None
                if message is None:
                    break
                writer.write(encode_jsonl(message))
                await writer.drain()
                if message.get("type") == "agent_end":
                    break
        finally:
            if queue is not None:
                self.pi_process.unsubscribe_events(queue)

    def _map_broker_to_pi_request(self, request: JsonObject) -> JsonObject:
        request_type = request.get("type")
        if request_type is None:
            return request

        pi_request_type = _BROKER_TO_PI_COMMAND.get(request_type, request_type)
        if request_type == pi_request_type:
            return request

        mapped = dict(request)
        mapped["type"] = pi_request_type
        return mapped

    def _should_stream_events(self, response: JsonObject) -> bool:
        return (
            response.get("type") == "response"
            and response.get("command") == "prompt"
            and response.get("success") is True
        )

    async def _ping(self, _request: JsonObject) -> JsonObject:
        return {"type": "pong", "session_id": self.paths.session_id}

    async def _status(self, _request: JsonObject) -> JsonObject:
        return {
            "type": "status",
            "metadata": self.metadata.as_dict(),
            "pi": self.pi_process.status(),
        }

    async def _shutdown(self, _request: JsonObject) -> JsonObject:
        self._shutdown_event.set()
        return {"type": "shutdown_ack", "session_id": self.paths.session_id}

    async def _extension_ui_response(self, request: JsonObject) -> JsonObject:
        ui_request_id = request.get("uiRequestId")
        if not isinstance(ui_request_id, str) or not ui_request_id:
            return {"type": "error", "error": "ui-response requires uiRequestId"}

        response_fields = [
            "cancelled" if request.get("cancelled") is True else None,
            "confirmed" if "confirmed" in request else None,
            "value" if "value" in request else None,
        ]
        present_fields = [field for field in response_fields if field is not None]
        if len(present_fields) != 1:
            return {
                "type": "error",
                "error": "ui-response requires exactly one of value, confirmed, or cancelled",
            }

        pi_response: JsonObject = {"type": "extension_ui_response", "id": ui_request_id}
        if request.get("cancelled") is True:
            pi_response["cancelled"] = True
        elif "confirmed" in request:
            confirmed = request.get("confirmed")
            if not isinstance(confirmed, bool):
                return {"type": "error", "error": "confirmed must be a boolean"}
            pi_response["confirmed"] = confirmed
        else:
            value = request.get("value")
            if not isinstance(value, str):
                return {"type": "error", "error": "value must be a string"}
            pi_response["value"] = value

        await self.pi_process.send_notification(pi_response)
        return {
            "type": "response",
            "command": "extension_ui_response",
            "success": True,
            "data": {"id": ui_request_id},
        }

    def _cleanup_runtime_files(self) -> None:
        for path in (self.paths.socket_path, self.paths.pid_path):
            with suppress(FileNotFoundError):
                Path(path).unlink()

"""Unix-socket broker lifecycle server for one pi-rpc session."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from contextlib import suppress
from pathlib import Path

from pi_rpc.broker.metadata import BrokerMetadata, utc_now_iso, write_metadata
from pi_rpc.broker.pi_process import PiRpcProcess
from pi_rpc.broker.schemas import BrokerSchemaError, validate_broker_request
from pi_rpc.paths import SessionPaths
from pi_rpc.transport.protocol import JsonObject, ProtocolError, decode_jsonl_line, encode_jsonl


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
                    response = await self._dispatch(request)
                except (ProtocolError, BrokerSchemaError) as exc:
                    response = {"type": "error", "error": str(exc)}
                writer.write(encode_jsonl(response))
                await writer.drain()
                if response.get("type") == "shutdown_ack":
                    break
        finally:
            writer.close()
            await writer.wait_closed()

    async def _dispatch(self, request: JsonObject) -> JsonObject:
        request_type = validate_broker_request(request)
        handlers: dict[str, Callable[[JsonObject], Awaitable[JsonObject]]] = {
            "ping": self._ping,
            "status": self._status,
            "shutdown": self._shutdown,
        }
        handler = handlers.get(request_type)
        if handler is None:
            return {"type": "error", "error": f"unsupported broker request: {request_type}"}
        return await handler(request)

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

    def _cleanup_runtime_files(self) -> None:
        for path in (self.paths.socket_path, self.paths.pid_path):
            with suppress(FileNotFoundError):
                Path(path).unlink()

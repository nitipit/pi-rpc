"""Managed `pi --mode rpc` subprocess for a broker."""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pi_rpc.transport.protocol import JsonObject, decode_jsonl_line, encode_jsonl

READY_TIMEOUT_SECONDS = 10.0
RECENT_STDERR_LINES = 20


class PiProcessError(RuntimeError):
    """Raised when the managed Pi RPC process fails."""


class PiRpcProcess:
    """Own and communicate with one `pi --mode rpc` child process."""

    def __init__(
        self,
        *,
        session_id: str | None,
        cwd: str,
        log_path: str | Path,
        pi_bin: str = "pi",
        name: str | None = None,
        no_session: bool = False,
        model: str | None = None,
        thinking: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.cwd = cwd
        self.log_path = Path(log_path)
        self.pi_bin = pi_bin
        self.name = name
        self.no_session = no_session
        self.model = model
        self.thinking = thinking
        self.process: asyncio.subprocess.Process | None = None
        self.ready = False
        self.last_state: JsonObject | None = None
        self.recent_events: deque[JsonObject] = deque(maxlen=50)
        self.recent_stderr: deque[str] = deque(maxlen=RECENT_STDERR_LINES)
        self._pending: dict[str, asyncio.Future[JsonObject]] = {}
        self._event_queues: set[asyncio.Queue[JsonObject]] = set()
        self._stdout_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None

    @property
    def pid(self) -> int | None:
        """Return the child pid when running."""
        return self.process.pid if self.process is not None else None

    @property
    def returncode(self) -> int | None:
        """Return the child process return code when known."""
        return self.process.returncode if self.process is not None else None

    async def start(self, *, ready_timeout: float = READY_TIMEOUT_SECONDS) -> None:
        """Start Pi RPC and wait until `get_state` succeeds."""
        if self.process is not None and self.returncode is None:
            return

        command = self._command()
        self.process = await asyncio.create_subprocess_exec(
            *command,
            cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._stdout_task = asyncio.create_task(self._read_stdout())
        self._stderr_task = asyncio.create_task(self._read_stderr())

        try:
            response = await asyncio.wait_for(
                self.send_command({"type": "get_state"}), timeout=ready_timeout
            )
        except Exception as exc:
            await self.stop()
            msg = f"Pi RPC process did not become ready: {exc}"
            raise PiProcessError(msg) from exc

        if not response.get("success"):
            await self.stop()
            msg = f"Pi RPC get_state failed: {response.get('error', response)}"
            raise PiProcessError(msg)

        data = response.get("data")
        self.last_state = data if isinstance(data, dict) else None
        self.ready = True

    async def send_command(self, command: JsonObject) -> JsonObject:
        """Send one Pi RPC command and wait for its correlated response."""
        if self.process is None or self.process.stdin is None or self.returncode is not None:
            msg = "Pi RPC process is not running"
            raise PiProcessError(msg)

        request_id = str(command.get("id") or uuid.uuid4())
        payload = {**command, "id": request_id}
        loop = asyncio.get_running_loop()
        future: asyncio.Future[JsonObject] = loop.create_future()
        self._pending[request_id] = future
        self.process.stdin.write(encode_jsonl(payload))
        await self.process.stdin.drain()
        return await future

    async def send_notification(self, command: JsonObject) -> None:
        """Send one Pi RPC notification that does not produce a response."""
        if self.process is None or self.process.stdin is None or self.returncode is not None:
            msg = "Pi RPC process is not running"
            raise PiProcessError(msg)

        self.process.stdin.write(encode_jsonl(command))
        await self.process.stdin.drain()

    async def stop(self) -> None:
        """Terminate the child process and reader tasks."""
        process = self.process
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except TimeoutError:
                process.kill()
                await process.wait()
        for task in (self._stdout_task, self._stderr_task):
            if task is not None:
                task.cancel()
        self.ready = False

    def subscribe_events(self) -> asyncio.Queue[JsonObject]:
        """Subscribe to future Pi RPC events."""
        queue: asyncio.Queue[JsonObject] = asyncio.Queue()
        self._event_queues.add(queue)
        return queue

    def unsubscribe_events(self, queue: asyncio.Queue[JsonObject]) -> None:
        """Remove a previously subscribed event queue."""
        self._event_queues.discard(queue)

    def status(self) -> dict[str, Any]:
        """Return current child process status."""
        return {
            "pid": self.pid,
            "ready": self.ready,
            "returncode": self.returncode,
            "recent_stderr": list(self.recent_stderr),
            "last_state": self.last_state,
        }

    def _command(self) -> Sequence[str]:
        command = [self.pi_bin, "--mode", "rpc"]
        if self.no_session:
            command.append("--no-session")
        elif self.session_id is not None:
            command.extend(["--session-id", self.session_id])
        else:
            msg = "Pi RPC process requires session_id unless no_session is enabled"
            raise PiProcessError(msg)
        if self.name:
            command.extend(["--name", self.name])
        if self.model:
            command.extend(["--model", self.model])
        if self.thinking:
            command.extend(["--thinking", self.thinking])
        return command

    async def _read_stdout(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        while line := await self.process.stdout.readline():
            try:
                message = decode_jsonl_line(line)
            except Exception as exc:
                self._reject_pending(PiProcessError(f"invalid Pi RPC stdout frame: {exc}"))
                continue
            if message.get("type") == "response" and isinstance(message.get("id"), str):
                request_id = message["id"]
                future = self._pending.pop(request_id, None)
                if future is not None and not future.done():
                    future.set_result(message)
            else:
                self.recent_events.append(message)
                for queue in list(self._event_queues):
                    queue.put_nowait(message)
        self._reject_pending(PiProcessError("Pi RPC stdout closed"))

    async def _read_stderr(self) -> None:
        assert self.process is not None
        assert self.process.stderr is not None
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("ab") as log_file:
            while line := await self.process.stderr.readline():
                text = line.decode("utf-8", errors="replace").rstrip("\r\n")
                self.recent_stderr.append(text)
                log_file.write(line)
                log_file.flush()

    def _reject_pending(self, error: Exception) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_exception(error)
        self._pending.clear()

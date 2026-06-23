"""Broker lifecycle operations used by the CLI."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from pi_rpc.client.broker import BrokerUnavailableError, request_broker
from pi_rpc.paths import paths_for_session
from pi_rpc.status import inspect_session

START_TIMEOUT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 0.05


class BrokerStartError(RuntimeError):
    """Raised when a broker cannot be started."""


async def broker_status(session_id: str) -> dict[str, Any] | None:
    """Return live broker status, or ``None`` when unavailable."""
    try:
        response = await request_broker(session_id, {"type": "status"})
    except BrokerUnavailableError:
        return None
    return response if response.get("type") == "status" else None


def start_broker(
    session_id: str,
    *,
    cwd: str | None = None,
    name: str | None = None,
    timeout: float = START_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Start a detached lifecycle broker for one session id."""
    existing = asyncio.run(broker_status(session_id))
    if existing is not None:
        return {"started": False, "status": existing}

    paths = paths_for_session(session_id)
    cwd_path = str(Path(cwd).resolve() if cwd else Path.cwd().resolve())
    paths.log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = paths.log_path.open("ab")

    command = [
        sys.executable,
        "-m",
        "pi_rpc.broker.main",
        "--session-id",
        session_id,
        "--cwd",
        cwd_path,
    ]
    if name:
        command.extend(["--name", name])

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_path
    )

    subprocess.Popen(
        command,
        cwd=cwd_path,
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
        close_fds=True,
    )
    log_file.close()

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = asyncio.run(broker_status(session_id))
        if status is not None:
            return {"started": True, "status": status}
        time.sleep(POLL_INTERVAL_SECONDS)

    view = inspect_session(session_id)
    msg = f"broker did not become ready for {session_id}; {view.note or 'no status available'}"
    raise BrokerStartError(msg)


def stop_broker(session_id: str) -> dict[str, Any]:
    """Ask a session broker to stop."""
    try:
        response = asyncio.run(request_broker(session_id, {"type": "shutdown"}))
    except BrokerUnavailableError:
        return {"stopped": False, "message": "broker is not running"}
    return {"stopped": response.get("type") == "shutdown_ack", "response": response}

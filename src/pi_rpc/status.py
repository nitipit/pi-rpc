"""Session status inspection for the current pi-rpc foundation."""

from __future__ import annotations

import os
from pathlib import Path

from pi_rpc.models import SessionStatusView
from pi_rpc.paths import paths_for_session


def pid_is_running(pid: int) -> bool:
    """Return whether a process id appears to be alive."""

    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid_file(path: str | Path) -> int | None:
    """Read a pid file, returning ``None`` when it is absent or invalid."""

    try:
        raw = Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def inspect_session(session_id: str) -> SessionStatusView:
    """Return the current local status for a pi-rpc session id."""

    paths = paths_for_session(session_id)
    pid = read_pid_file(str(paths.pid_path))
    if pid is None:
        status = "stopped"
        note = "Broker is not running. Use `pi-rpc start --session-id ...` to start it."
    elif pid_is_running(pid):
        status = "running"
        note = f"Broker pid {pid} appears to be running."
    else:
        status = "stale"
        note = f"Broker pid file exists, but pid {pid} is not running."

    return SessionStatusView(
        session_id=paths.session_id,
        status=status,
        socket_path=str(paths.socket_path),
        pid_path=str(paths.pid_path),
        metadata_path=str(paths.metadata_path),
        log_path=str(paths.log_path),
        note=note,
    )

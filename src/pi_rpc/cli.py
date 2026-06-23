"""Command-line interface for pi-rpc."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import NoReturn

from cyclopts import App

from pi_rpc.lifecycle import BrokerStartError, broker_status, start_broker, stop_broker
from pi_rpc.models import OutputFormat, SessionStatusView
from pi_rpc.paths import known_metadata_paths, paths_for_session
from pi_rpc.session_id import SessionIdError, session_identity
from pi_rpc.status import inspect_session

app = App(help="Remote control for long-running Pi RPC sessions.")


def main() -> None:
    """Run the pi-rpc command-line application."""

    app()


def _exit_invalid_session(error: SessionIdError) -> NoReturn:
    print(f"Invalid --session-id: {error}", file=sys.stderr)
    raise SystemExit(2)


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _broker_status_human(data: dict[str, object]) -> None:
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        _print_json(data)
        return
    print(f"Session: {metadata.get('session_id')}")
    print("Status:  running")
    print(f"Broker:  {metadata.get('broker_pid')}")
    print(f"Pi PID:  {metadata.get('pi_pid')}")
    print(f"Ready:   {metadata.get('pi_ready')}")
    print(f"Socket:  {metadata.get('socket_path')}")
    print(f"State:   {metadata.get('metadata_path')}")
    print(f"Log:     {metadata.get('log_path')}")
    print(f"CWD:     {metadata.get('cwd')}")
    if metadata.get("name"):
        print(f"Name:    {metadata.get('name')}")


def _status_human(view: SessionStatusView) -> None:
    print(f"Session: {view.session_id}")
    print(f"Status:  {view.status}")
    print(f"Socket:  {view.socket_path}")
    print(f"PID:     {view.pid_path}")
    print(f"State:   {view.metadata_path}")
    print(f"Log:     {view.log_path}")
    if view.note:
        print(f"Note:    {view.note}")


@app.default
def help_default() -> None:
    """Show help when no command is provided."""

    app.help_print()


@app.command(name="validate-session-id")
def validate_session_id_cmd(*, session_id: str) -> None:
    """Validate a readable pi-rpc session id.

    Parameters
    ----------
    session_id
        Stable readable session handle to validate.
    """

    try:
        identity = session_identity(session_id)
    except SessionIdError as exc:
        _exit_invalid_session(exc)
    print(identity.value)


@app.command(name="paths")
def paths_command(*, session_id: str, output: OutputFormat = "human") -> None:
    """Show local runtime and state paths for a session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        paths = paths_for_session(session_id)
    except SessionIdError as exc:
        _exit_invalid_session(exc)

    data = paths.as_dict()
    if output == "json":
        _print_json(data)
        return

    print(f"Session:  {data['session_id']}")
    print(f"File key: {data['file_stem']}")
    print(f"Socket:   {data['socket_path']}")
    print(f"PID:      {data['pid_path']}")
    print(f"State:    {data['metadata_path']}")
    print(f"Log:      {data['log_path']}")


@app.command
def start(
    *,
    session_id: str,
    name: str | None = None,
    cwd: str | None = None,
    pi_bin: str = "pi",
    output: OutputFormat = "human",
) -> None:
    """Start the local broker for a Pi RPC session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    name
        Optional friendly display name to record in broker metadata.
    cwd
        Working directory to associate with the session broker.
    pi_bin
        Pi executable to start in RPC mode.
    output
        Output format: human or json.
    """

    try:
        result = start_broker(session_id, cwd=cwd, name=name, pi_bin=pi_bin)
    except SessionIdError as exc:
        _exit_invalid_session(exc)
    except BrokerStartError as exc:
        print(f"Failed to start broker: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if output == "json":
        _print_json(result)
        return

    if result["started"]:
        print(f"Started broker for session {session_id}.")
    else:
        print(f"Broker for session {session_id} is already running.")
    _broker_status_human(result["status"])


@app.command
def stop(*, session_id: str, output: OutputFormat = "human") -> None:
    """Stop the local broker for a Pi RPC session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        result = stop_broker(session_id)
    except SessionIdError as exc:
        _exit_invalid_session(exc)

    if output == "json":
        _print_json(result)
        return

    print(f"Stopped broker for session {session_id}." if result["stopped"] else result["message"])


@app.command
def status(*, session_id: str, output: OutputFormat = "human") -> None:
    """Inspect local status for a managed Pi RPC session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        live = asyncio.run(broker_status(session_id))
        view = inspect_session(session_id) if live is None else None
    except SessionIdError as exc:
        _exit_invalid_session(exc)

    if live is not None:
        if output == "json":
            _print_json(live)
        else:
            _broker_status_human(live)
        return

    assert view is not None
    if output == "json":
        _print_json(view.as_dict())
    else:
        _status_human(view)


@app.command
def sessions(*, output: OutputFormat = "human") -> None:
    """List known pi-rpc session metadata files."""

    metadata_paths = known_metadata_paths()
    data = [{"metadata_path": str(path)} for path in metadata_paths]

    if output == "json":
        _print_json({"sessions": data})
        return

    if not metadata_paths:
        print("No pi-rpc sessions are known yet.")
        return

    print("Known session metadata files:")
    for path in metadata_paths:
        print(f"- {path}")

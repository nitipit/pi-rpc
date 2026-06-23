"""Command-line interface for pi-rpc."""

from __future__ import annotations

import json
import sys
from typing import NoReturn

from cyclopts import App

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
        view = inspect_session(session_id)
    except SessionIdError as exc:
        _exit_invalid_session(exc)

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

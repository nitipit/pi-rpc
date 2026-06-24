"""Lifecycle and local path commands."""

from __future__ import annotations

import asyncio
import sys

from cyclopts import App

from pi_rpc.cli_support.common import (
    broker_status_human,
    exit_invalid_session,
    print_json,
    status_human,
)
from pi_rpc.lifecycle import BrokerStartError, broker_status, start_broker, stop_broker
from pi_rpc.models import OutputFormat
from pi_rpc.paths import known_metadata_paths, paths_for_session
from pi_rpc.session_id import SessionIdError, session_identity
from pi_rpc.status import inspect_session


def register(app: App) -> None:
    """Register lifecycle commands."""

    @app.default
    def help_default() -> None:
        """Show help when no command is provided."""

        app.help_print()

    @app.command(name="validate-session-id")
    def validate_session_id_cmd(*, session_id: str) -> None:
        """Validate a readable pi-rpc session id."""

        try:
            identity = session_identity(session_id)
        except SessionIdError as exc:
            exit_invalid_session(exc)
        print(identity.value)

    @app.command(name="paths")
    def paths_command(*, session_id: str, output: OutputFormat = "human") -> None:
        """Show local runtime and state paths for a session."""

        try:
            paths = paths_for_session(session_id)
        except SessionIdError as exc:
            exit_invalid_session(exc)

        data = paths.as_dict()
        if output == "json":
            print_json(data)
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
        """Start the local broker for a Pi RPC session."""

        try:
            result = start_broker(session_id, cwd=cwd, name=name, pi_bin=pi_bin)
        except SessionIdError as exc:
            exit_invalid_session(exc)
        except BrokerStartError as exc:
            print(f"Failed to start broker: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

        if output == "json":
            print_json(result)
            return

        if result["started"]:
            print(f"Started broker for session {session_id}.")
        else:
            print(f"Broker for session {session_id} is already running.")
        broker_status_human(result["status"])

    @app.command
    def stop(*, session_id: str, output: OutputFormat = "human") -> None:
        """Stop the local broker for a Pi RPC session."""

        try:
            result = stop_broker(session_id)
        except SessionIdError as exc:
            exit_invalid_session(exc)

        if output == "json":
            print_json(result)
            return

        print(
            f"Stopped broker for session {session_id}." if result["stopped"] else result["message"]
        )

    @app.command
    def status(*, session_id: str, output: OutputFormat = "human") -> None:
        """Inspect local status for a managed Pi RPC session."""

        try:
            live = asyncio.run(broker_status(session_id))
            view = inspect_session(session_id) if live is None else None
        except SessionIdError as exc:
            exit_invalid_session(exc)

        if live is not None:
            if output == "json":
                print_json(live)
            else:
                broker_status_human(live)
            return

        assert view is not None
        if output == "json":
            print_json(view.as_dict())
        else:
            status_human(view)

    @app.command
    def sessions(*, output: OutputFormat = "human") -> None:
        """List known pi-rpc session metadata files."""

        metadata_paths = known_metadata_paths()
        data = [{"metadata_path": str(path)} for path in metadata_paths]

        if output == "json":
            print_json({"sessions": data})
            return

        if not metadata_paths:
            print("No pi-rpc sessions are known yet.")
            return

        print("Known session metadata files:")
        for path in metadata_paths:
            print(f"- {path}")

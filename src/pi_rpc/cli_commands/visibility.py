"""Read-only visibility commands."""

from __future__ import annotations

import asyncio
import sys

from cyclopts import App

from pi_rpc.cli_support.common import exit_invalid_session
from pi_rpc.cli_support.runners import run_read_only_command
from pi_rpc.client.broker import BrokerUnavailableError
from pi_rpc.models import OutputFormat
from pi_rpc.session_id import SessionIdError


def _handle_error(exc: BrokerUnavailableError) -> None:
    print(f"Broker unavailable: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def register(app: App) -> None:
    """Register visibility commands."""

    @app.command(name="fork-messages")
    def fork_messages(*, session_id: str, output: OutputFormat = "human") -> None:
        """Show fork messages for the current branch."""

        try:
            asyncio.run(
                run_read_only_command(
                    session_id=session_id, broker_command="fork-messages", output=output
                )
            )
        except BrokerUnavailableError as exc:
            _handle_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def state(*, session_id: str, output: OutputFormat = "human") -> None:
        """Show live state from the running Pi session."""

        try:
            asyncio.run(
                run_read_only_command(session_id=session_id, broker_command="state", output=output)
            )
        except BrokerUnavailableError as exc:
            _handle_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def models(*, session_id: str, output: OutputFormat = "human") -> None:
        """List available Pi models for the running session."""

        try:
            asyncio.run(
                run_read_only_command(session_id=session_id, broker_command="models", output=output)
            )
        except BrokerUnavailableError as exc:
            _handle_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def stats(*, session_id: str, output: OutputFormat = "human") -> None:
        """Show session statistics."""

        try:
            asyncio.run(
                run_read_only_command(session_id=session_id, broker_command="stats", output=output)
            )
        except BrokerUnavailableError as exc:
            _handle_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def messages(*, session_id: str, output: OutputFormat = "human") -> None:
        """Show recent messages in a compact listing."""

        try:
            asyncio.run(
                run_read_only_command(
                    session_id=session_id, broker_command="messages", output=output
                )
            )
        except BrokerUnavailableError as exc:
            _handle_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="last-assistant-text")
    def last_assistant_text(*, session_id: str, output: OutputFormat = "human") -> None:
        """Show the last assistant text."""

        try:
            asyncio.run(
                run_read_only_command(
                    session_id=session_id, broker_command="last-assistant-text", output=output
                )
            )
        except BrokerUnavailableError as exc:
            _handle_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def commands(*, session_id: str, output: OutputFormat = "human") -> None:
        """Show known Pi commands for the session."""

        try:
            asyncio.run(
                run_read_only_command(
                    session_id=session_id, broker_command="commands", output=output
                )
            )
        except BrokerUnavailableError as exc:
            _handle_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

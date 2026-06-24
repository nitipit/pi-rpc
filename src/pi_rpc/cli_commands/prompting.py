"""Prompting and run-control commands."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from cyclopts import App

from pi_rpc.cli_support.common import exit_invalid_session
from pi_rpc.cli_support.extension_ui import parse_confirmed
from pi_rpc.cli_support.payloads import StreamingBehavior
from pi_rpc.cli_support.runners import (
    run_abort_bash_command,
    run_bash_command,
    run_control_command,
    run_prompt,
    run_ui_response_command,
)
from pi_rpc.cli_support.stateless import run_stateless_prompt
from pi_rpc.client.broker import BrokerUnavailableError
from pi_rpc.models import OutputFormat
from pi_rpc.session_id import SessionIdError


def _handle_common_errors(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        print(f"Invalid image attachment: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if isinstance(exc, BrokerUnavailableError):
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if isinstance(exc, SessionIdError):
        exit_invalid_session(exc)
    raise exc


def register(app: App) -> None:
    """Register prompt and run-control commands."""

    @app.command
    def run(
        *,
        message: str,
        output: OutputFormat = "human",
        interactive_ui: bool = True,
        image: list[str] | None = None,
        cwd: str | None = None,
        pi_bin: str = "pi",
        model: str | None = None,
        thinking: str | None = None,
        detach: bool = False,
    ) -> None:
        """Run one stateless disposable Pi RPC task."""

        try:
            if detach:
                from pi_rpc.jobs.manager import start_stateless_run_job

                job = start_stateless_run_job(
                    message=message,
                    image_paths=image,
                    cwd=str(Path.cwd() if cwd is None else Path(cwd)),
                    pi_bin=pi_bin,
                    model=model,
                    thinking=thinking,
                )
                if output == "json":
                    from pi_rpc.cli_support.common import print_json

                    print_json(job.as_dict())
                else:
                    print(f"Started stateless job {job.job_id}.")
                return

            asyncio.run(
                run_stateless_prompt(
                    message=message,
                    output=output,
                    interactive_ui=interactive_ui,
                    image_paths=image,
                    cwd=str(Path.cwd() if cwd is None else Path(cwd)),
                    pi_bin=pi_bin,
                    model=model,
                    thinking=thinking,
                )
            )
        except (ValueError, BrokerUnavailableError, SessionIdError) as exc:
            _handle_common_errors(exc)

    @app.command
    def prompt(
        *,
        session_id: str,
        message: str,
        output: OutputFormat = "human",
        interactive_ui: bool = True,
        streaming_behavior: StreamingBehavior | None = None,
        image: list[str] | None = None,
        detach: bool = False,
    ) -> None:
        """Send a prompt to the managed Pi session and stream events."""

        try:
            if detach:
                from pi_rpc.jobs.manager import start_stateful_prompt_job

                job = start_stateful_prompt_job(
                    session_id=session_id,
                    message=message,
                    image_paths=image,
                    streaming_behavior=streaming_behavior,
                )
                if output == "json":
                    from pi_rpc.cli_support.common import print_json

                    print_json(job.as_dict())
                else:
                    print(f"Started job {job.job_id} for session {session_id}.")
                return

            asyncio.run(
                run_prompt(
                    session_id=session_id,
                    message=message,
                    output=output,
                    interactive_ui=interactive_ui,
                    streaming_behavior=streaming_behavior,
                    image_paths=image,
                )
            )
        except (ValueError, BrokerUnavailableError, SessionIdError) as exc:
            _handle_common_errors(exc)

    @app.command
    def steer(
        *,
        session_id: str,
        message: str,
        output: OutputFormat = "human",
        image: list[str] | None = None,
    ) -> None:
        """Queue a steering message while the session is running."""

        try:
            asyncio.run(
                run_control_command(
                    session_id=session_id,
                    command="steer",
                    message=message,
                    output=output,
                    image_paths=image,
                )
            )
        except (ValueError, BrokerUnavailableError, SessionIdError) as exc:
            _handle_common_errors(exc)

    @app.command(name="follow-up")
    def follow_up(
        *,
        session_id: str,
        message: str,
        output: OutputFormat = "human",
        image: list[str] | None = None,
    ) -> None:
        """Queue a follow-up message to be processed after current work finishes."""

        try:
            asyncio.run(
                run_control_command(
                    session_id=session_id,
                    command="follow_up",
                    message=message,
                    output=output,
                    image_paths=image,
                )
            )
        except (ValueError, BrokerUnavailableError, SessionIdError) as exc:
            _handle_common_errors(exc)

    @app.command
    def abort(*, session_id: str, output: OutputFormat = "human") -> None:
        """Abort the current in-progress agent operation."""

        try:
            asyncio.run(run_control_command(session_id=session_id, command="abort", output=output))
        except (BrokerUnavailableError, SessionIdError) as exc:
            _handle_common_errors(exc)

    @app.command(name="abort-bash")
    def abort_bash(*, session_id: str, output: OutputFormat = "human") -> None:
        """Abort the most recent running bash command."""

        try:
            asyncio.run(run_abort_bash_command(session_id=session_id, output=output))
        except (BrokerUnavailableError, SessionIdError) as exc:
            _handle_common_errors(exc)

    @app.command(name="ui-respond")
    def ui_respond(
        ui_request_id: str,
        *,
        session_id: str,
        value: str | None = None,
        confirmed: str | None = None,
        cancelled: bool = False,
        output: OutputFormat = "human",
    ) -> None:
        """Respond to a pending extension UI request."""

        try:
            asyncio.run(
                run_ui_response_command(
                    session_id=session_id,
                    ui_request_id=ui_request_id,
                    value=value,
                    confirmed=parse_confirmed(confirmed),
                    cancelled=cancelled,
                    output=output,
                )
            )
        except BrokerUnavailableError as exc:
            print(f"Broker unavailable: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        except SessionIdError as exc:
            exit_invalid_session(exc)
        except ValueError as exc:
            print(f"Invalid UI response: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc

    @app.command
    def bash(
        command: str,
        *,
        session_id: str,
        output: OutputFormat = "human",
        exclude_from_context: bool = False,
    ) -> None:
        """Run a shell command in the active Pi session."""

        try:
            asyncio.run(
                run_bash_command(
                    session_id=session_id,
                    command=command,
                    output=output,
                    exclude_from_context=exclude_from_context,
                )
            )
        except (BrokerUnavailableError, SessionIdError) as exc:
            _handle_common_errors(exc)

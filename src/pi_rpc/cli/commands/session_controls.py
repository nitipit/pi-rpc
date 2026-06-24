"""Stateful session control commands."""

from __future__ import annotations

import asyncio
import sys

from cyclopts import App

from pi_rpc.cli.support.common import exit_invalid_session
from pi_rpc.cli.support.runners import (
    run_abort_retry_command,
    run_auto_compaction_command,
    run_auto_retry_command,
    run_compact_command,
    run_control_request,
    run_follow_up_mode_command,
    run_model_command,
    run_name_command,
    run_steering_mode_command,
    run_thinking_command,
)
from pi_rpc.cli.support.summaries import print_cycle_model_summary, print_cycle_thinking_summary
from pi_rpc.client.broker import BrokerUnavailableError
from pi_rpc.models import OutputFormat
from pi_rpc.session_id import SessionIdError
from pi_rpc.transport.protocol import JsonObject

THINKING_LEVELS = ("off", "minimal", "low", "medium", "high", "xhigh")
ThinkingLevel = str
AUTO_MODES = ("on", "off")
AutoMode = str
SESSION_MODES = ("all", "one-at-a-time")
SteeringMode = str


def _broker_error(exc: BrokerUnavailableError) -> None:
    print(f"Broker unavailable: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def register(app: App) -> None:
    """Register session control commands."""

    @app.command(name="new-session")
    def new_session(
        *,
        session_id: str,
        parent_session: str | None = None,
        output: OutputFormat = "human",
    ) -> None:
        """Create a new Pi session, optionally from a parent session."""

        request: JsonObject = {"type": "new-session"}
        if parent_session is not None:
            request["parentSession"] = parent_session

        try:
            asyncio.run(
                run_control_request(
                    session_id=session_id,
                    request=request,
                    expected_command="new_session",
                    output=output,
                    command_label="new-session",
                )
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="switch-session")
    def switch_session(
        session_path: str,
        *,
        session_id: str,
        output: OutputFormat = "human",
    ) -> None:
        """Switch to an existing branch session path."""

        try:
            asyncio.run(
                run_control_request(
                    session_id=session_id,
                    request={"type": "switch-session", "sessionPath": session_path},
                    expected_command="switch_session",
                    output=output,
                    command_label="switch-session",
                )
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def clone(*, session_id: str, output: OutputFormat = "human") -> None:
        """Clone the current active branch into a new session."""

        try:
            asyncio.run(
                run_control_request(
                    session_id=session_id,
                    request={"type": "clone"},
                    expected_command="clone",
                    output=output,
                    command_label="clone",
                )
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="fork")
    def fork(entry_id: str, *, session_id: str, output: OutputFormat = "human") -> None:
        """Create a new branch from an existing session entry id."""

        try:
            asyncio.run(
                run_control_request(
                    session_id=session_id,
                    request={"type": "fork", "entryId": entry_id},
                    expected_command="fork",
                    output=output,
                    command_label="fork",
                )
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="export-html")
    def export_html(
        *,
        session_id: str,
        output_path: str | None = None,
        output: OutputFormat = "human",
    ) -> None:
        """Export current session as HTML."""

        request: JsonObject = {"type": "export-html"}
        if output_path is not None:
            request["outputPath"] = output_path

        try:
            asyncio.run(
                run_control_request(
                    session_id=session_id,
                    request=request,
                    expected_command="export_html",
                    output=output,
                    command_label="export-html",
                )
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def model(model: str, *, session_id: str, output: OutputFormat = "human") -> None:
        """Set the active model for the running session."""

        try:
            asyncio.run(run_model_command(session_id=session_id, model=model, output=output))
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)
        except ValueError as exc:
            print(f"Model resolution failed: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        except RuntimeError as exc:
            print(f"Model command failed: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

    @app.command(name="cycle-model")
    def cycle_model(*, session_id: str, output: OutputFormat = "human") -> None:
        """Rotate through available models for the session."""

        try:
            asyncio.run(
                run_control_request(
                    session_id=session_id,
                    request={"type": "cycle-model"},
                    expected_command="cycle_model",
                    output=output,
                    command_label="cycle-model",
                    response_printer=print_cycle_model_summary,
                )
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def thinking(level: ThinkingLevel, *, session_id: str, output: OutputFormat = "human") -> None:
        """Set thinking intensity for the running session."""

        if level not in THINKING_LEVELS:
            print(f"Invalid thinking level: {level}", file=sys.stderr)
            raise SystemExit(1)

        try:
            asyncio.run(run_thinking_command(session_id=session_id, level=level, output=output))
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="cycle-thinking")
    def cycle_thinking(*, session_id: str, output: OutputFormat = "human") -> None:
        """Rotate through thinking levels for the running session."""

        try:
            asyncio.run(
                run_control_request(
                    session_id=session_id,
                    request={"type": "cycle-thinking"},
                    expected_command="cycle_thinking_level",
                    output=output,
                    command_label="cycle-thinking",
                    response_printer=print_cycle_thinking_summary,
                )
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="name")
    def set_session_name(name: str, *, session_id: str, output: OutputFormat = "human") -> None:
        """Set the active session name."""

        try:
            asyncio.run(run_name_command(session_id=session_id, name=name, output=output))
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command
    def compact(
        *, session_id: str, instructions: str | None = None, output: OutputFormat = "human"
    ) -> None:
        """Trigger conversation compaction with optional custom instructions."""

        try:
            asyncio.run(
                run_compact_command(session_id=session_id, instructions=instructions, output=output)
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="auto-compaction")
    def auto_compaction(mode: AutoMode, *, session_id: str, output: OutputFormat = "human") -> None:
        """Enable or disable automatic compaction."""

        if mode not in AUTO_MODES:
            print(f"Invalid auto-compaction mode: {mode}", file=sys.stderr)
            raise SystemExit(1)
        try:
            asyncio.run(
                run_auto_compaction_command(session_id=session_id, auto=mode, output=output)
            )
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="auto-retry")
    def auto_retry(mode: AutoMode, *, session_id: str, output: OutputFormat = "human") -> None:
        """Enable or disable automatic retries."""

        if mode not in AUTO_MODES:
            print(f"Invalid auto-retry mode: {mode}", file=sys.stderr)
            raise SystemExit(1)
        try:
            asyncio.run(run_auto_retry_command(session_id=session_id, auto=mode, output=output))
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="steering-mode")
    def steering_mode(
        mode: SteeringMode, *, session_id: str, output: OutputFormat = "human"
    ) -> None:
        """Set steering behavior mode."""

        if mode not in SESSION_MODES:
            print(f"Invalid steering mode: {mode}", file=sys.stderr)
            raise SystemExit(1)
        try:
            asyncio.run(run_steering_mode_command(session_id=session_id, mode=mode, output=output))
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="follow-up-mode")
    def follow_up_mode(
        mode: SteeringMode, *, session_id: str, output: OutputFormat = "human"
    ) -> None:
        """Set follow-up message behavior mode."""

        if mode not in SESSION_MODES:
            print(f"Invalid follow-up mode: {mode}", file=sys.stderr)
            raise SystemExit(1)
        try:
            asyncio.run(run_follow_up_mode_command(session_id=session_id, mode=mode, output=output))
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

    @app.command(name="abort-retry")
    def abort_retry(*, session_id: str, output: OutputFormat = "human") -> None:
        """Abort automatic retrying behavior for the session."""

        try:
            asyncio.run(run_abort_retry_command(session_id=session_id, output=output))
        except BrokerUnavailableError as exc:
            _broker_error(exc)
        except SessionIdError as exc:
            exit_invalid_session(exc)

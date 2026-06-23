"""Command-line interface for pi-rpc."""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Callable
from typing import Literal, NoReturn, cast

from cyclopts import App

from pi_rpc.client.broker import BrokerUnavailableError, request_broker, stream_broker
from pi_rpc.lifecycle import BrokerStartError, broker_status, start_broker, stop_broker
from pi_rpc.models import OutputFormat, SessionStatusView
from pi_rpc.paths import known_metadata_paths, paths_for_session
from pi_rpc.session_id import SessionIdError, session_identity
from pi_rpc.status import inspect_session
from pi_rpc.transport.protocol import JsonObject

THINKING_LEVELS = ("off", "minimal", "low", "medium", "high", "xhigh")
ThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh"]

PI_READ_ONLY_COMMANDS = {
    "state": "get_state",
    "models": "get_available_models",
    "stats": "get_session_stats",
    "messages": "get_messages",
    "last-assistant-text": "get_last_assistant_text",
    "commands": "get_commands",
}

app = App(help="Remote control for long-running Pi RPC sessions.")


def main() -> None:
    """Run the pi-rpc command-line application."""

    app()


def _exit_invalid_session(error: SessionIdError) -> NoReturn:
    print(f"Invalid --session-id: {error}", file=sys.stderr)
    raise SystemExit(2)


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _print_json_frame(data: object) -> None:
    print(json.dumps(data, sort_keys=True))


def _print_text_delta(event: JsonObject) -> None:
    """Print assistant text delta chunks from message_update events."""

    if event.get("type") != "message_update":
        return

    assistant_event = event.get("assistantMessageEvent")
    if not isinstance(assistant_event, dict):
        return
    if assistant_event.get("type") != "text_delta":
        return
    delta = assistant_event.get("delta")
    if isinstance(delta, str):
        print(delta, end="", flush=True)


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


async def _run_prompt(*, session_id: str, message: str, output: OutputFormat) -> None:
    """Send a prompt command and stream the Pi RPC event response."""

    saw_response = False
    accepted = False
    async for frame in stream_broker(session_id, {"type": "prompt", "message": message}):
        if output == "json":
            _print_json_frame(frame)
            if frame.get("type") == "response":
                saw_response = True
                accepted = frame.get("success") is True
                if not accepted:
                    raise SystemExit(1)
            continue

        if frame.get("type") == "response":
            saw_response = True
            accepted = frame.get("command") == "prompt" and frame.get("success") is True
            if not accepted:
                error = frame.get("error", "prompt was not accepted")
                print(f"Prompt failed: {error}", file=sys.stderr)
                raise SystemExit(1)
            continue

        if frame.get("type") == "agent_end":
            print()

        _print_text_delta(frame)

    if not saw_response:
        print("No prompt response from broker.", file=sys.stderr)
        raise SystemExit(1)
    if output == "human" and not accepted:
        raise SystemExit(1)


async def _run_control_command(
    *,
    session_id: str,
    command: str,
    output: OutputFormat,
    message: str | None = None,
) -> None:
    """Send a Pi runtime control command and handle response semantics."""

    request: JsonObject = {"type": command}
    if message is not None:
        request["message"] = message

    await _run_control_request(
        session_id=session_id,
        request=request,
        expected_command=command,
        output=output,
        command_label=command.replace("_", "-"),
    )


async def _run_control_request(
    *,
    session_id: str,
    request: JsonObject,
    expected_command: str,
    output: OutputFormat,
    command_label: str | None = None,
    response_printer: Callable[[JsonObject], None] | None = None,
) -> None:
    """Send a mapped Pi control command and print output according to format."""

    await _run_command_and_print(
        session_id=session_id,
        request=request,
        expected_command=expected_command,
        output=output,
        command_label=command_label,
        response_printer=response_printer,
    )


async def _run_read_only_command(
    *,
    session_id: str,
    broker_command: str,
    output: OutputFormat,
) -> None:
    """Send a read-only mapped Pi command and print a human summary."""

    pi_command = PI_READ_ONLY_COMMANDS[broker_command]
    await _run_command_and_print(
        session_id=session_id,
        request={"type": broker_command},
        expected_command=pi_command,
        output=output,
        command_label=broker_command,
        response_printer=lambda response: _print_command_summary(broker_command, response),
    )


async def _run_model_command(
    *,
    session_id: str,
    model: str,
    output: OutputFormat,
) -> None:
    """Resolve and set the active model."""

    resolved_model = await _resolve_model_for_session(session_id=session_id, requested_model=model)
    await _run_control_request(
        session_id=session_id,
        request={"type": "model", "model": resolved_model},
        expected_command="set_model",
        output=output,
        command_label="model",
        response_printer=lambda response: _print_model_summary(response, resolved_model),
    )


async def _run_thinking_command(
    *,
    session_id: str,
    level: ThinkingLevel,
    output: OutputFormat,
) -> None:
    """Set the thinking level for the session."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "thinking", "level": level},
        expected_command="set_thinking_level",
        output=output,
        command_label="thinking",
        response_printer=lambda response: _print_thinking_level_summary(response, level),
    )


def _model_ref(model: object) -> str | None:
    """Return a provider/id reference from a Pi model object or string."""

    if isinstance(model, str):
        return model
    if not isinstance(model, dict):
        return None

    provider = model.get("provider")
    model_id = model.get("id")
    if isinstance(provider, str) and isinstance(model_id, str):
        return f"{provider}/{model_id}"
    if isinstance(model_id, str):
        return model_id
    return None


def _extract_model_refs(data: object) -> list[str]:
    """Extract model references from Pi get_available_models response data."""

    models = data.get("models") if isinstance(data, dict) else data
    if not isinstance(models, list):
        return []
    return [model_ref for model in models if (model_ref := _model_ref(model)) is not None]


def _resolve_model_from_available_models(
    *,
    available: list[str],
    requested_model: str,
) -> str:
    """Resolve a model token from available model names."""

    if requested_model in available:
        return requested_model

    if "/" in requested_model:
        msg = f"Unknown model '{requested_model}'."
        raise ValueError(msg)

    matching_models = [model for model in available if model.split("/")[-1] == requested_model]
    if not matching_models:
        msg = f"Unknown model '{requested_model}'."
        raise ValueError(msg)
    if len(matching_models) > 1:
        joined = ", ".join(matching_models)
        msg = f"Ambiguous model '{requested_model}': {joined}"
        raise ValueError(msg)
    return matching_models[0]


async def _resolve_model_for_session(
    *,
    session_id: str,
    requested_model: str,
) -> str:
    """Load available models from broker and resolve the requested model."""

    response = await request_broker(session_id, {"type": "models"})
    if (
        response.get("type") != "response"
        or response.get("command") != "get_available_models"
        or response.get("success") is not True
    ):
        msg = "Could not load available models before setting model."
        raise RuntimeError(msg)

    available_models = _extract_model_refs(response.get("data"))
    if not available_models:
        msg = "Invalid response format from models command."
        raise RuntimeError(msg)

    return _resolve_model_from_available_models(
        available=available_models, requested_model=requested_model
    )


def _print_command_summary(command: str, response: JsonObject) -> None:
    """Print a compact human-readable summary for read-only responses."""

    data = response.get("data")
    print(f"{command.replace('-', ' ').replace('_', ' ').title()} response:")

    if command == "messages":
        _print_messages_summary(data)
        return

    if command == "last-assistant-text":
        _print_last_assistant_text_summary(data)
        return

    if command == "commands":
        _print_commands_summary(data)
        return

    if command == "models":
        models = _extract_model_refs(data)
        if models:
            print(f"  models: {len(models)} available")
            for model in models:
                print(f"  - {model}")
            return

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                rendered = json.dumps(value, sort_keys=True)
            else:
                rendered = str(value)
            print(f"  {key}: {rendered}")
        if data:
            return

    if isinstance(data, list):
        for item in data:
            print(f"  - {item}")
        return

    print(f"  data: {data}")


def _print_messages_summary(data: object) -> None:
    messages = data if isinstance(data, list) else []
    if not messages:
        print("  (no messages)")
        return

    for message in messages:
        if not isinstance(message, dict):
            print(f"  - {message}")
            continue

        role = message.get("role", "unknown")
        content = message.get("content")
        if isinstance(content, list):
            rendered_parts: list[str] = []
            for chunk in content:
                if isinstance(chunk, dict) and isinstance(chunk.get("text"), str):
                    rendered_parts.append(cast("str", chunk.get("text")))
                elif isinstance(chunk, str):
                    rendered_parts.append(chunk)
            content_text = "\n".join(rendered_parts)
        elif isinstance(content, str):
            content_text = content
        else:
            content_text = str(content)

        print(f"  {role}: {content_text}")


def _print_last_assistant_text_summary(data: object) -> None:
    text = ""
    if isinstance(data, str):
        text = data
    elif isinstance(data, dict):
        if isinstance(data.get("text"), str):
            text = cast("str", data.get("text"))
    elif isinstance(data, list) and data and isinstance(data[0], str):
        text = data[0]

    if not text:
        print("  (no assistant text yet)")
        return

    print(f"  {text}")


def _print_commands_summary(data: object) -> None:
    commands = data if isinstance(data, list) else []
    if not commands:
        print("  (no commands)")
        return

    for command in commands:
        if not isinstance(command, dict):
            print(f"  - {command}")
            continue

        name = command.get("name") or command.get("command") or "<unnamed>"
        description = command.get("description")
        source = command.get("source")
        line = f"  /{name}"
        if source:
            line = f"{line} [{source}]"
        if description:
            line = f"{line}: {description}"
        print(line)


def _print_model_summary(response: JsonObject, resolved_model: str) -> None:
    data = response.get("data")
    model = resolved_model
    if isinstance(data, dict):
        maybe_model = data.get("model")
        if isinstance(maybe_model, str):
            model = maybe_model

    print(f"  model: {model}")


def _print_cycle_model_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("model"), str):
        print(f"  model: {data['model']}")
        return

    print("  model cycle: done")


def _print_thinking_level_summary(response: JsonObject, level: str) -> None:
    data = response.get("data")
    resolved = level
    if isinstance(data, dict):
        maybe_level = data.get("level")
        if isinstance(maybe_level, str):
            resolved = maybe_level

    print(f"  thinking: {resolved}")


def _print_cycle_thinking_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("level"), str):
        print(f"  thinking: {data['level']}")
        return

    print("  thinking cycle: done")


async def _run_command_and_print(
    *,
    session_id: str,
    request: JsonObject,
    output: OutputFormat,
    expected_command: str,
    command_label: str | None = None,
    response_printer: Callable[[JsonObject], None] | None = None,
) -> None:
    """Send one broker/Pi command and print output according to format."""

    response = await request_broker(session_id, request)

    if output == "json":
        _print_json_frame(response)
        if (
            response.get("type") != "response"
            or response.get("command") != expected_command
            or response.get("success") is not True
        ):
            raise SystemExit(1)
        return

    if response.get("type") != "response":
        print("Broker did not return a valid response command frame.", file=sys.stderr)
        raise SystemExit(1)

    if response.get("command") != expected_command:
        print(f"Unexpected command response: {response.get('command')}", file=sys.stderr)
        raise SystemExit(1)

    if response.get("success") is not True:
        label = command_label or expected_command
        error = response.get("error", f"{label} was not accepted")
        print(f"{label} failed: {error}", file=sys.stderr)
        raise SystemExit(1)

    if response_printer is not None:
        response_printer(response)
    elif output == "human":
        label = command_label or expected_command
        print(f"{label} sent")


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
def prompt(
    *,
    session_id: str,
    message: str,
    output: OutputFormat = "human",
) -> None:
    """Send a prompt to the managed Pi session and stream events.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    message
        Prompt content to send via Pi RPC.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(_run_prompt(session_id=session_id, message=message, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def steer(*, session_id: str, message: str, output: OutputFormat = "human") -> None:
    """Queue a steering message while the session is running.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    message
        Steering text to send to the active Pi session.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_control_command(
                session_id=session_id, command="steer", message=message, output=output
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="follow-up")
def follow_up(*, session_id: str, message: str, output: OutputFormat = "human") -> None:
    """Queue a follow-up message to be processed after current work finishes.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    message
        Follow-up text to send via Pi RPC.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_control_command(
                session_id=session_id, command="follow_up", message=message, output=output
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def abort(*, session_id: str, output: OutputFormat = "human") -> None:
    """Abort the current in-progress agent operation.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(_run_control_command(session_id=session_id, command="abort", output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def state(*, session_id: str, output: OutputFormat = "human") -> None:
    """Show live state from the running Pi session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_read_only_command(session_id=session_id, broker_command="state", output=output)
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def model(
    model: str,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Set the active model for the running session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    model
        Desired model (provider/id or unique bare id).
    output
        Output format: human or json.
    """

    try:
        asyncio.run(_run_model_command(session_id=session_id, model=model, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)
    except ValueError as exc:
        print(f"Model resolution failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except RuntimeError as exc:
        print(f"Model command failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


@app.command(name="cycle-model")
def cycle_model(*, session_id: str, output: OutputFormat = "human") -> None:
    """Rotate through available models for the session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_control_request(
                session_id=session_id,
                request={"type": "cycle-model"},
                expected_command="cycle_model",
                output=output,
                command_label="cycle-model",
                response_printer=_print_cycle_model_summary,
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def thinking(
    level: ThinkingLevel,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Set thinking intensity for the running session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    level
        Thinking level: off, minimal, low, medium, high, or xhigh.
    output
        Output format: human or json.
    """

    if level not in THINKING_LEVELS:
        print(f"Invalid thinking level: {level}", file=sys.stderr)
        raise SystemExit(1)

    try:
        asyncio.run(_run_thinking_command(session_id=session_id, level=level, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="cycle-thinking")
def cycle_thinking(*, session_id: str, output: OutputFormat = "human") -> None:
    """Rotate through thinking levels for the running session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_control_request(
                session_id=session_id,
                request={"type": "cycle-thinking"},
                expected_command="cycle_thinking_level",
                output=output,
                command_label="cycle-thinking",
                response_printer=_print_cycle_thinking_summary,
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def models(*, session_id: str, output: OutputFormat = "human") -> None:
    """List available Pi models for the running session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_read_only_command(session_id=session_id, broker_command="models", output=output)
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def stats(*, session_id: str, output: OutputFormat = "human") -> None:
    """Show session statistics.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_read_only_command(session_id=session_id, broker_command="stats", output=output)
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def messages(*, session_id: str, output: OutputFormat = "human") -> None:
    """Show recent messages in a compact listing.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_read_only_command(session_id=session_id, broker_command="messages", output=output)
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="last-assistant-text")
def last_assistant_text(*, session_id: str, output: OutputFormat = "human") -> None:
    """Show the last assistant text.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_read_only_command(
                session_id=session_id, broker_command="last-assistant-text", output=output
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def commands(*, session_id: str, output: OutputFormat = "human") -> None:
    """Show known Pi commands for the session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_read_only_command(session_id=session_id, broker_command="commands", output=output)
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


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

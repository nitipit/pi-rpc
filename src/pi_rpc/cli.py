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
AUTO_MODES = ("on", "off")
AutoMode = Literal["on", "off"]
SESSION_MODES = ("all", "one-at-a-time")
SteeringMode = Literal["all", "one-at-a-time"]

PI_READ_ONLY_COMMANDS = {
    "state": "get_state",
    "models": "get_available_models",
    "stats": "get_session_stats",
    "messages": "get_messages",
    "last-assistant-text": "get_last_assistant_text",
    "commands": "get_commands",
    "fork-messages": "get_fork_messages",
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


def _print_extension_ui_request(event: JsonObject, *, session_id: str) -> None:
    """Print a compact notice for extension UI requests during human streaming."""

    if event.get("type") != "extension_ui_request":
        return

    request_id = event.get("id")
    method = event.get("method")
    title = event.get("title") or event.get("message") or "extension UI request"
    print()
    print(f"Extension UI request: {method} {request_id}")
    print(f"  {title}")
    if isinstance(request_id, str):
        print(f"  respond: pi-rpc ui-respond --session-id {session_id} {request_id} ...")


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

        _print_extension_ui_request(frame, session_id=session_id)
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
    model_request: JsonObject = {"type": "model"}
    if "/" in resolved_model:
        provider, model_id = resolved_model.split("/", 1)
        model_request["provider"] = provider
        model_request["modelId"] = model_id
    else:
        model_request["model"] = resolved_model

    await _run_control_request(
        session_id=session_id,
        request=model_request,
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


async def _run_name_command(
    *,
    session_id: str,
    name: str,
    output: OutputFormat,
) -> None:
    """Rename the active session for later UI and traceability."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "name", "name": name},
        expected_command="set_session_name",
        output=output,
        command_label="name",
        response_printer=lambda response: _print_name_summary(response, name),
    )


async def _run_compact_command(
    *,
    session_id: str,
    instructions: str | None,
    output: OutputFormat,
) -> None:
    """Request compaction, optionally with custom instructions."""

    request: JsonObject = {"type": "compact"}
    if instructions is not None:
        request["customInstructions"] = instructions

    await _run_control_request(
        session_id=session_id,
        request=request,
        expected_command="compact",
        output=output,
        command_label="compact",
        response_printer=lambda response: _print_compact_summary(response, instructions),
    )


async def _run_auto_compaction_command(
    *,
    session_id: str,
    auto: AutoMode,
    output: OutputFormat,
) -> None:
    """Set automatic compaction enabled state."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "auto-compaction", "enabled": auto == "on"},
        expected_command="set_auto_compaction",
        output=output,
        command_label="auto-compaction",
        response_printer=lambda response: _print_auto_state_summary(
            response, "auto-compaction", auto
        ),
    )


async def _run_auto_retry_command(
    *,
    session_id: str,
    auto: AutoMode,
    output: OutputFormat,
) -> None:
    """Set automatic retry enabled state."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "auto-retry", "enabled": auto == "on"},
        expected_command="set_auto_retry",
        output=output,
        command_label="auto-retry",
        response_printer=lambda response: _print_auto_state_summary(response, "auto-retry", auto),
    )


async def _run_steering_mode_command(
    *,
    session_id: str,
    mode: SteeringMode,
    output: OutputFormat,
) -> None:
    """Set steering mode behavior."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "steering-mode", "mode": mode},
        expected_command="set_steering_mode",
        output=output,
        command_label="steering-mode",
        response_printer=lambda response: _print_mode_summary(response, "steering-mode", mode),
    )


async def _run_follow_up_mode_command(
    *,
    session_id: str,
    mode: SteeringMode,
    output: OutputFormat,
) -> None:
    """Set follow-up mode behavior."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "follow-up-mode", "mode": mode},
        expected_command="set_follow_up_mode",
        output=output,
        command_label="follow-up-mode",
        response_printer=lambda response: _print_mode_summary(response, "follow-up-mode", mode),
    )


async def _run_abort_retry_command(
    *,
    session_id: str,
    output: OutputFormat,
) -> None:
    """Abort a retry loop, if active."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "abort-retry"},
        expected_command="abort_retry",
        output=output,
        command_label="abort-retry",
        response_printer=_print_abort_retry_summary,
    )


async def _run_bash_command(
    *,
    session_id: str,
    command: str,
    output: OutputFormat,
) -> None:
    """Run a shell command in the active session."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "bash", "command": command},
        expected_command="bash",
        output=output,
        command_label="bash",
        response_printer=_print_bash_summary,
    )


async def _run_abort_bash_command(
    *,
    session_id: str,
    output: OutputFormat,
) -> None:
    """Abort a running bash command."""

    await _run_control_request(
        session_id=session_id,
        request={"type": "abort_bash"},
        expected_command="abort_bash",
        output=output,
        command_label="abort-bash",
        response_printer=_print_abort_bash_summary,
    )


async def _run_ui_response_command(
    *,
    session_id: str,
    ui_request_id: str,
    value: str | None,
    confirmed: bool | None,
    cancelled: bool,
    output: OutputFormat,
) -> None:
    """Send an extension UI dialog response without waiting for Pi output."""

    request = _build_ui_response_request(
        ui_request_id=ui_request_id,
        value=value,
        confirmed=confirmed,
        cancelled=cancelled,
    )
    await _run_command_and_print(
        session_id=session_id,
        request=request,
        expected_command="extension_ui_response",
        output=output,
        command_label="ui-respond",
        response_printer=_print_ui_response_summary,
    )


def _parse_confirmed(value: str | None) -> bool | None:
    """Parse a CLI confirmation value into a boolean."""

    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "y", "1"}:
        return True
    if normalized in {"false", "no", "n", "0"}:
        return False
    msg = "--confirmed must be true/false, yes/no, or 1/0."
    raise ValueError(msg)


def _build_ui_response_request(
    *,
    ui_request_id: str,
    value: str | None,
    confirmed: bool | None,
    cancelled: bool,
) -> JsonObject:
    """Build a validated broker request for an extension UI response."""

    if not ui_request_id:
        msg = "UI request id is required."
        raise ValueError(msg)

    provided = int(value is not None) + int(confirmed is not None) + int(cancelled)
    if provided != 1:
        msg = "Provide exactly one of --value, --confirmed, or --cancelled."
        raise ValueError(msg)

    request: JsonObject = {"type": "ui-response", "uiRequestId": ui_request_id}
    if cancelled:
        request["cancelled"] = True
    elif confirmed is not None:
        request["confirmed"] = confirmed
    else:
        assert value is not None
        request["value"] = value
    return request


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
    model = _model_ref(data) or resolved_model
    if isinstance(data, dict):
        nested_model = data.get("model")
        model = _model_ref(nested_model) or model

    print(f"  model: {model}")


def _print_cycle_model_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict):
        model = _model_ref(data.get("model"))
        if model is not None:
            print(f"  model: {model}")
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


def _print_name_summary(response: JsonObject, fallback: str) -> None:
    data = response.get("data")
    name = fallback
    if isinstance(data, dict):
        maybe_name = data.get("name")
        if isinstance(maybe_name, str):
            name = maybe_name
    print(f"  name: {name}")


def _print_compact_summary(response: JsonObject, instructions: str | None) -> None:
    data = response.get("data")
    if instructions is None:
        print("  compact: triggered")
        return

    if isinstance(data, dict) and isinstance(data.get("customInstructions"), str):
        instructions = cast("str", data.get("customInstructions"))

    preview = (instructions[:50] + "…") if len(instructions) > 50 else instructions
    print(f"  compact: custom instructions set ({len(instructions)} chars)")
    print(f"  instructions: {preview}")


def _print_auto_state_summary(response: JsonObject, label: str, auto: AutoMode) -> None:
    data = response.get("data")
    state = auto
    if isinstance(data, dict) and isinstance(data.get("enabled"), bool):
        state = "on" if data.get("enabled") else "off"
    print(f"  {label}: {state}")


def _print_mode_summary(response: JsonObject, label: str, mode: SteeringMode) -> None:
    data = response.get("data")
    value = mode
    if isinstance(data, dict) and isinstance(data.get("mode"), str):
        value = str(data.get("mode"))
    print(f"  {label}: {value}")


def _print_abort_retry_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("aborted"), bool):
        if data.get("aborted"):
            print("  abort-retry: aborted")
        else:
            print("  abort-retry: nothing to abort")
        return

    print("  abort-retry: sent")


def _print_bash_summary(response: JsonObject) -> None:
    data = response.get("data")
    if not isinstance(data, dict):
        print("  bash: no output")
        return

    exit_code = data.get("exitCode", data.get("exit_code"))
    if isinstance(exit_code, int):
        print(f"  exitCode: {exit_code}")

    cancelled = data.get("cancelled")
    if isinstance(cancelled, bool):
        print(f"  cancelled: {cancelled}")

    truncated = data.get("truncated")
    if isinstance(truncated, bool):
        print(f"  truncated: {truncated}")

    output = data.get("output")
    if isinstance(output, str):
        print(f"  output: {output}")
        return

    output_path = data.get("outputPath", data.get("path", data.get("output_path")))
    if isinstance(output_path, str):
        print(f"  path: {output_path}")


def _print_abort_bash_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("aborted"), bool):
        if data.get("aborted"):
            print("  abort-bash: aborted")
        else:
            print("  abort-bash: nothing to abort")
        return

    print("  abort-bash: success")


def _print_ui_response_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("id"), str):
        print(f"  ui-response: sent for {data['id']}")
        return
    print("  ui-response: sent")


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


@app.command(name="abort-bash")
def abort_bash(*, session_id: str, output: OutputFormat = "human") -> None:
    """Abort the most recent running bash command.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(_run_abort_bash_command(session_id=session_id, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


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
    """Respond to a pending extension UI request.

    Parameters
    ----------
    ui_request_id
        The id from an ``extension_ui_request`` event.
    session_id
        Stable readable session handle.
    value
        Value for select, input, or editor requests.
    confirmed
        Boolean response for confirm requests.
    cancelled
        Cancel/dismiss any dialog request.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_ui_response_command(
                session_id=session_id,
                ui_request_id=ui_request_id,
                value=value,
                confirmed=_parse_confirmed(confirmed),
                cancelled=cancelled,
                output=output,
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)
    except ValueError as exc:
        print(f"Invalid UI response: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


@app.command
def bash(
    command: str,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Run a shell command in the active Pi session.

    Parameters
    ----------
    command
        Shell command text to execute.
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(_run_bash_command(session_id=session_id, command=command, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="new-session")
def new_session(
    *,
    session_id: str,
    parent_session: str | None = None,
    output: OutputFormat = "human",
) -> None:
    """Create a new Pi session, optionally from a parent session.

    Parameters
    ----------
    session_id
        Stable readable source session handle.
    parent_session
        Optional parent session path for branching.
    output
        Output format: human or json.
    """

    request: JsonObject = {"type": "new-session"}
    if parent_session is not None:
        request["parentSession"] = parent_session

    try:
        asyncio.run(
            _run_control_request(
                session_id=session_id,
                request=request,
                expected_command="new_session",
                output=output,
                command_label="new-session",
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="switch-session")
def switch_session(
    session_path: str,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Switch to an existing branch session path.

    Parameters
    ----------
    session_path
        Absolute or repository-relative path used by Pi as ``sessionPath``.
    session_id
        Stable readable source session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_control_request(
                session_id=session_id,
                request={"type": "switch-session", "sessionPath": session_path},
                expected_command="switch_session",
                output=output,
                command_label="switch-session",
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def clone(
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Clone the current active branch into a new session.

    Parameters
    ----------
    session_id
        Stable readable source session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_control_request(
                session_id=session_id,
                request={"type": "clone"},
                expected_command="clone",
                output=output,
                command_label="clone",
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="fork")
def fork(
    entry_id: str,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Create a new branch from an existing session entry id.

    Parameters
    ----------
    entry_id
        Entry id to fork from.
    session_id
        Stable readable source session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_control_request(
                session_id=session_id,
                request={"type": "fork", "entryId": entry_id},
                expected_command="fork",
                output=output,
                command_label="fork",
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="fork-messages")
def fork_messages(*, session_id: str, output: OutputFormat = "human") -> None:
    """Show fork messages for the current branch.

    Parameters
    ----------
    session_id
        Stable readable source session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_read_only_command(
                session_id=session_id, broker_command="fork-messages", output=output
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="export-html")
def export_html(
    *,
    session_id: str,
    output_path: str | None = None,
    output: OutputFormat = "human",
) -> None:
    """Export current session as HTML.

    Parameters
    ----------
    session_id
        Stable readable source session handle.
    output_path
        Optional output path for the generated HTML export.
    output
        Output format: human or json.
    """

    request: JsonObject = {"type": "export-html"}
    if output_path is not None:
        request["outputPath"] = output_path

    try:
        asyncio.run(
            _run_control_request(
                session_id=session_id,
                request=request,
                expected_command="export_html",
                output=output,
                command_label="export-html",
            )
        )
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


@app.command(name="name")
def set_session_name(
    name: str,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Set the active session name.

    Parameters
    ----------
    name
        New session name.
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(_run_name_command(session_id=session_id, name=name, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command
def compact(
    *,
    session_id: str,
    instructions: str | None = None,
    output: OutputFormat = "human",
) -> None:
    """Trigger conversation compaction with optional custom instructions.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    instructions
        Optional custom instructions to guide compaction.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(
            _run_compact_command(session_id=session_id, instructions=instructions, output=output)
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="auto-compaction")
def auto_compaction(
    mode: AutoMode,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Enable or disable automatic compaction.

    Parameters
    ----------
    mode
        "on" to enable, "off" to disable.
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    if mode not in AUTO_MODES:
        print(f"Invalid auto-compaction mode: {mode}", file=sys.stderr)
        raise SystemExit(1)

    try:
        asyncio.run(
            _run_auto_compaction_command(
                session_id=session_id,
                auto=mode,
                output=output,
            )
        )
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="auto-retry")
def auto_retry(
    mode: AutoMode,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Enable or disable automatic retries.

    Parameters
    ----------
    mode
        "on" to enable, "off" to disable.
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    if mode not in AUTO_MODES:
        print(f"Invalid auto-retry mode: {mode}", file=sys.stderr)
        raise SystemExit(1)

    try:
        asyncio.run(_run_auto_retry_command(session_id=session_id, auto=mode, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="steering-mode")
def steering_mode(
    mode: SteeringMode,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Set steering behavior mode.

    Parameters
    ----------
    mode
        "all" or "one-at-a-time".
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    if mode not in SESSION_MODES:
        print(f"Invalid steering mode: {mode}", file=sys.stderr)
        raise SystemExit(1)

    try:
        asyncio.run(_run_steering_mode_command(session_id=session_id, mode=mode, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="follow-up-mode")
def follow_up_mode(
    mode: SteeringMode,
    *,
    session_id: str,
    output: OutputFormat = "human",
) -> None:
    """Set follow-up message behavior mode.

    Parameters
    ----------
    mode
        "all" or "one-at-a-time".
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    if mode not in SESSION_MODES:
        print(f"Invalid follow-up mode: {mode}", file=sys.stderr)
        raise SystemExit(1)

    try:
        asyncio.run(_run_follow_up_mode_command(session_id=session_id, mode=mode, output=output))
    except BrokerUnavailableError as exc:
        print(f"Broker unavailable: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except SessionIdError as exc:
        _exit_invalid_session(exc)


@app.command(name="abort-retry")
def abort_retry(*, session_id: str, output: OutputFormat = "human") -> None:
    """Abort automatic retrying behavior for the session.

    Parameters
    ----------
    session_id
        Stable readable session handle.
    output
        Output format: human or json.
    """

    try:
        asyncio.run(_run_abort_retry_command(session_id=session_id, output=output))
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

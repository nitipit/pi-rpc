"""Async command runners used by CLI command modules."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from pi_rpc.cli.support.common import print_json_frame, print_text_delta
from pi_rpc.cli.support.extension_ui import (
    build_ui_response_request,
    maybe_interactive_extension_ui_response,
    print_extension_ui_request,
)
from pi_rpc.cli.support.model_resolution import resolve_model_for_session
from pi_rpc.cli.support.payloads import (
    build_bash_request,
    build_message_request,
    build_prompt_request,
)
from pi_rpc.cli.support.summaries import (
    print_abort_bash_summary,
    print_abort_retry_summary,
    print_auto_state_summary,
    print_bash_summary,
    print_command_summary,
    print_compact_summary,
    print_mode_summary,
    print_model_summary,
    print_name_summary,
    print_thinking_level_summary,
    print_ui_response_summary,
)
from pi_rpc.client.broker import request_broker, stream_broker
from pi_rpc.models import OutputFormat
from pi_rpc.transport.protocol import JsonObject

AutoMode = str
SteeringMode = str
StreamingBehavior = str
ThinkingLevel = str

PI_READ_ONLY_COMMANDS = {
    "state": "get_state",
    "models": "get_available_models",
    "stats": "get_session_stats",
    "messages": "get_messages",
    "last-assistant-text": "get_last_assistant_text",
    "commands": "get_commands",
    "fork-messages": "get_fork_messages",
}


async def run_prompt(
    *,
    session_id: str,
    message: str,
    output: OutputFormat,
    interactive_ui: bool,
    streaming_behavior: StreamingBehavior | None,
    image_paths: Sequence[str] | None,
) -> None:
    """Send a prompt command and stream the Pi RPC event response."""

    saw_response = False
    accepted = False
    async for frame in stream_broker(
        session_id,
        build_prompt_request(
            message=message,
            streaming_behavior=streaming_behavior,
            image_paths=image_paths,
        ),
    ):
        if output == "json":
            print_json_frame(frame)
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

        can_interact = interactive_ui and sys.stdin.isatty()
        print_extension_ui_request(frame, session_id=session_id, manual_hint=not can_interact)
        await maybe_interactive_extension_ui_response(
            frame,
            session_id=session_id,
            interactive_ui=interactive_ui,
        )
        print_text_delta(frame)

    if not saw_response:
        print("No prompt response from broker.", file=sys.stderr)
        raise SystemExit(1)
    if output == "human" and not accepted:
        raise SystemExit(1)


async def run_control_command(
    *,
    session_id: str,
    command: str,
    output: OutputFormat,
    message: str | None = None,
    image_paths: Sequence[str] | None = None,
) -> None:
    """Send a Pi runtime control command and handle response semantics."""

    request = build_message_request(
        command=command,
        message=message,
        image_paths=image_paths,
    )

    await run_control_request(
        session_id=session_id,
        request=request,
        expected_command=command,
        output=output,
        command_label=command.replace("_", "-"),
    )


async def run_control_request(
    *,
    session_id: str,
    request: JsonObject,
    expected_command: str,
    output: OutputFormat,
    command_label: str | None = None,
    response_printer: Callable[[JsonObject], None] | None = None,
) -> None:
    """Send a mapped Pi control command and print output according to format."""

    await run_command_and_print(
        session_id=session_id,
        request=request,
        expected_command=expected_command,
        output=output,
        command_label=command_label,
        response_printer=response_printer,
    )


async def run_read_only_command(
    *,
    session_id: str,
    broker_command: str,
    output: OutputFormat,
) -> None:
    """Send a read-only mapped Pi command and print a human summary."""

    pi_command = PI_READ_ONLY_COMMANDS[broker_command]
    await run_command_and_print(
        session_id=session_id,
        request={"type": broker_command},
        expected_command=pi_command,
        output=output,
        command_label=broker_command,
        response_printer=lambda response: print_command_summary(broker_command, response),
    )


async def run_model_command(
    *,
    session_id: str,
    model: str,
    output: OutputFormat,
) -> None:
    """Resolve and set the active model."""

    resolved_model = await resolve_model_for_session(session_id=session_id, requested_model=model)
    model_request: JsonObject = {"type": "model"}
    if "/" in resolved_model:
        provider, model_id = resolved_model.split("/", 1)
        model_request["provider"] = provider
        model_request["modelId"] = model_id
    else:
        model_request["model"] = resolved_model

    await run_control_request(
        session_id=session_id,
        request=model_request,
        expected_command="set_model",
        output=output,
        command_label="model",
        response_printer=lambda response: print_model_summary(response, resolved_model),
    )


async def run_thinking_command(
    *,
    session_id: str,
    level: ThinkingLevel,
    output: OutputFormat,
) -> None:
    """Set the thinking level for the session."""

    await run_control_request(
        session_id=session_id,
        request={"type": "thinking", "level": level},
        expected_command="set_thinking_level",
        output=output,
        command_label="thinking",
        response_printer=lambda response: print_thinking_level_summary(response, level),
    )


async def run_name_command(
    *,
    session_id: str,
    name: str,
    output: OutputFormat,
) -> None:
    """Rename the active session for later UI and traceability."""

    await run_control_request(
        session_id=session_id,
        request={"type": "name", "name": name},
        expected_command="set_session_name",
        output=output,
        command_label="name",
        response_printer=lambda response: print_name_summary(response, name),
    )


async def run_compact_command(
    *,
    session_id: str,
    instructions: str | None,
    output: OutputFormat,
) -> None:
    """Request compaction, optionally with custom instructions."""

    request: JsonObject = {"type": "compact"}
    if instructions is not None:
        request["customInstructions"] = instructions

    await run_control_request(
        session_id=session_id,
        request=request,
        expected_command="compact",
        output=output,
        command_label="compact",
        response_printer=lambda response: print_compact_summary(response, instructions),
    )


async def run_auto_compaction_command(
    *,
    session_id: str,
    auto: AutoMode,
    output: OutputFormat,
) -> None:
    """Set automatic compaction enabled state."""

    await run_control_request(
        session_id=session_id,
        request={"type": "auto-compaction", "enabled": auto == "on"},
        expected_command="set_auto_compaction",
        output=output,
        command_label="auto-compaction",
        response_printer=lambda response: print_auto_state_summary(
            response, "auto-compaction", auto
        ),
    )


async def run_auto_retry_command(
    *,
    session_id: str,
    auto: AutoMode,
    output: OutputFormat,
) -> None:
    """Set automatic retry enabled state."""

    await run_control_request(
        session_id=session_id,
        request={"type": "auto-retry", "enabled": auto == "on"},
        expected_command="set_auto_retry",
        output=output,
        command_label="auto-retry",
        response_printer=lambda response: print_auto_state_summary(response, "auto-retry", auto),
    )


async def run_steering_mode_command(
    *,
    session_id: str,
    mode: SteeringMode,
    output: OutputFormat,
) -> None:
    """Set steering mode behavior."""

    await run_control_request(
        session_id=session_id,
        request={"type": "steering-mode", "mode": mode},
        expected_command="set_steering_mode",
        output=output,
        command_label="steering-mode",
        response_printer=lambda response: print_mode_summary(response, "steering-mode", mode),
    )


async def run_follow_up_mode_command(
    *,
    session_id: str,
    mode: SteeringMode,
    output: OutputFormat,
) -> None:
    """Set follow-up mode behavior."""

    await run_control_request(
        session_id=session_id,
        request={"type": "follow-up-mode", "mode": mode},
        expected_command="set_follow_up_mode",
        output=output,
        command_label="follow-up-mode",
        response_printer=lambda response: print_mode_summary(response, "follow-up-mode", mode),
    )


async def run_abort_retry_command(
    *,
    session_id: str,
    output: OutputFormat,
) -> None:
    """Abort a retry loop, if active."""

    await run_control_request(
        session_id=session_id,
        request={"type": "abort-retry"},
        expected_command="abort_retry",
        output=output,
        command_label="abort-retry",
        response_printer=print_abort_retry_summary,
    )


async def run_bash_command(
    *,
    session_id: str,
    command: str,
    output: OutputFormat,
    exclude_from_context: bool,
) -> None:
    """Run a shell command in the active session."""

    await run_control_request(
        session_id=session_id,
        request=build_bash_request(
            command=command,
            exclude_from_context=exclude_from_context,
        ),
        expected_command="bash",
        output=output,
        command_label="bash",
        response_printer=print_bash_summary,
    )


async def run_abort_bash_command(
    *,
    session_id: str,
    output: OutputFormat,
) -> None:
    """Abort a running bash command."""

    await run_control_request(
        session_id=session_id,
        request={"type": "abort_bash"},
        expected_command="abort_bash",
        output=output,
        command_label="abort-bash",
        response_printer=print_abort_bash_summary,
    )


async def run_ui_response_command(
    *,
    session_id: str,
    ui_request_id: str,
    value: str | None,
    confirmed: bool | None,
    cancelled: bool,
    output: OutputFormat,
) -> None:
    """Send an extension UI dialog response without waiting for Pi output."""

    request = build_ui_response_request(
        ui_request_id=ui_request_id,
        value=value,
        confirmed=confirmed,
        cancelled=cancelled,
    )
    await run_command_and_print(
        session_id=session_id,
        request=request,
        expected_command="extension_ui_response",
        output=output,
        command_label="ui-respond",
        response_printer=print_ui_response_summary,
    )


async def run_command_and_print(
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
        print_json_frame(response)
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

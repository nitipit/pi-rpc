"""Human summary printers for CLI command responses."""

from __future__ import annotations

import json
from typing import cast

from pi_rpc.cli.support.model_resolution import extract_model_refs, model_ref
from pi_rpc.transport.protocol import JsonObject

AutoMode = str
SteeringMode = str


def print_command_summary(command: str, response: JsonObject) -> None:
    """Print a compact human-readable summary for read-only responses."""

    data = response.get("data")
    print(f"{command.replace('-', ' ').replace('_', ' ').title()} response:")

    if command == "messages":
        print_messages_summary(data)
        return

    if command == "last-assistant-text":
        print_last_assistant_text_summary(data)
        return

    if command == "commands":
        print_commands_summary(data)
        return

    if command == "models":
        models = extract_model_refs(data)
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


def print_messages_summary(data: object) -> None:
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


def print_last_assistant_text_summary(data: object) -> None:
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


def print_commands_summary(data: object) -> None:
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


def print_model_summary(response: JsonObject, resolved_model: str) -> None:
    data = response.get("data")
    model = model_ref(data) or resolved_model
    if isinstance(data, dict):
        nested_model = data.get("model")
        model = model_ref(nested_model) or model

    print(f"  model: {model}")


def print_cycle_model_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict):
        model = model_ref(data.get("model"))
        if model is not None:
            print(f"  model: {model}")
            return

    print("  model cycle: done")


def print_thinking_level_summary(response: JsonObject, level: str) -> None:
    data = response.get("data")
    resolved = level
    if isinstance(data, dict):
        maybe_level = data.get("level")
        if isinstance(maybe_level, str):
            resolved = maybe_level

    print(f"  thinking: {resolved}")


def print_cycle_thinking_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("level"), str):
        print(f"  thinking: {data['level']}")
        return

    print("  thinking cycle: done")


def print_name_summary(response: JsonObject, fallback: str) -> None:
    data = response.get("data")
    name = fallback
    if isinstance(data, dict):
        maybe_name = data.get("name")
        if isinstance(maybe_name, str):
            name = maybe_name
    print(f"  name: {name}")


def print_compact_summary(response: JsonObject, instructions: str | None) -> None:
    data = response.get("data")
    if instructions is None:
        print("  compact: triggered")
        return

    if isinstance(data, dict) and isinstance(data.get("customInstructions"), str):
        instructions = cast("str", data.get("customInstructions"))

    preview = (instructions[:50] + "…") if len(instructions) > 50 else instructions
    print(f"  compact: custom instructions set ({len(instructions)} chars)")
    print(f"  instructions: {preview}")


def print_auto_state_summary(response: JsonObject, label: str, auto: AutoMode) -> None:
    data = response.get("data")
    state = auto
    if isinstance(data, dict) and isinstance(data.get("enabled"), bool):
        state = "on" if data.get("enabled") else "off"
    print(f"  {label}: {state}")


def print_mode_summary(response: JsonObject, label: str, mode: SteeringMode) -> None:
    data = response.get("data")
    value = mode
    if isinstance(data, dict) and isinstance(data.get("mode"), str):
        value = str(data.get("mode"))
    print(f"  {label}: {value}")


def print_abort_retry_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("aborted"), bool):
        if data.get("aborted"):
            print("  abort-retry: aborted")
        else:
            print("  abort-retry: nothing to abort")
        return

    print("  abort-retry: sent")


def print_bash_summary(response: JsonObject) -> None:
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


def print_abort_bash_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("aborted"), bool):
        if data.get("aborted"):
            print("  abort-bash: aborted")
        else:
            print("  abort-bash: nothing to abort")
        return

    print("  abort-bash: success")


def print_ui_response_summary(response: JsonObject) -> None:
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("id"), str):
        print(f"  ui-response: sent for {data['id']}")
        return
    print("  ui-response: sent")

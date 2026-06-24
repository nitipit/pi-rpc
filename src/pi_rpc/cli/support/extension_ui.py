"""Extension UI helpers for prompt streams."""

from __future__ import annotations

import sys
from collections.abc import Callable

from pi_rpc.client.broker import request_broker
from pi_rpc.transport.protocol import JsonObject

DIALOG_UI_METHODS = {"select", "confirm", "input", "editor"}


def print_extension_ui_request(
    event: JsonObject,
    *,
    session_id: str | None,
    manual_hint: bool,
) -> None:
    """Print a compact notice for extension UI requests during human streaming."""

    if event.get("type") != "extension_ui_request":
        return

    request_id = event.get("id")
    method = event.get("method")
    title = event.get("title") or event.get("message") or "extension UI request"
    print()
    print(f"Extension UI request: {method} {request_id}")
    print(f"  {title}")
    if (
        manual_hint
        and session_id is not None
        and isinstance(request_id, str)
        and isinstance(method, str)
        and method in DIALOG_UI_METHODS
    ):
        print(f"  respond: pi-rpc ui-respond --session-id {session_id} {request_id} ...")


def extension_ui_request_to_response(
    event: JsonObject,
    read_line: Callable[[str], str] = input,
) -> JsonObject | None:
    """Prompt for a dialog extension UI response and return a broker request."""

    if event.get("type") != "extension_ui_request":
        return None

    request_id = event.get("id")
    method = event.get("method")
    if not isinstance(request_id, str) or not isinstance(method, str):
        return None
    if method == "select":
        return _select_ui_response_request(event, request_id, read_line)
    if method == "confirm":
        return _confirm_ui_response_request(request_id, read_line)
    if method == "input":
        return _input_ui_response_request(event, request_id, read_line)
    if method == "editor":
        return _editor_ui_response_request(event, request_id, read_line)
    return None


def _select_ui_response_request(
    event: JsonObject,
    request_id: str,
    read_line: Callable[[str], str],
) -> JsonObject | None:
    """Build a response request for a select dialog."""

    raw_options = event.get("options")
    if not isinstance(raw_options, list):
        return None
    options = [option for option in raw_options if isinstance(option, str)]
    if not options:
        return None

    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option}")

    while True:
        answer = read_line("  Choose 1-N, exact value, or /cancel: ").strip()
        if answer == "/cancel" or answer == "":
            return build_ui_response_request(
                ui_request_id=request_id,
                value=None,
                confirmed=None,
                cancelled=True,
            )
        if answer.isdigit():
            index = int(answer)
            if 1 <= index <= len(options):
                return build_ui_response_request(
                    ui_request_id=request_id,
                    value=options[index - 1],
                    confirmed=None,
                    cancelled=False,
                )
        if answer in options:
            return build_ui_response_request(
                ui_request_id=request_id,
                value=answer,
                confirmed=None,
                cancelled=False,
            )
        print("  Invalid selection.")


def _confirm_ui_response_request(
    request_id: str,
    read_line: Callable[[str], str],
) -> JsonObject:
    """Build a response request for a confirm dialog."""

    while True:
        answer = read_line("  Confirm? [y/n, /cancel]: ").strip().lower()
        if answer == "/cancel":
            return build_ui_response_request(
                ui_request_id=request_id,
                value=None,
                confirmed=None,
                cancelled=True,
            )
        if answer in {"y", "yes"}:
            return build_ui_response_request(
                ui_request_id=request_id,
                value=None,
                confirmed=True,
                cancelled=False,
            )
        if answer in {"", "n", "no"}:
            return build_ui_response_request(
                ui_request_id=request_id,
                value=None,
                confirmed=False,
                cancelled=False,
            )
        print("  Please answer y, n, or /cancel.")


def _input_ui_response_request(
    event: JsonObject,
    request_id: str,
    read_line: Callable[[str], str],
) -> JsonObject:
    """Build a response request for an input dialog."""

    placeholder = event.get("placeholder")
    prompt = "  Value"
    if isinstance(placeholder, str) and placeholder:
        prompt += f" ({placeholder})"
    prompt += " [/cancel to cancel]: "
    answer = read_line(prompt)
    if answer == "/cancel":
        return build_ui_response_request(
            ui_request_id=request_id,
            value=None,
            confirmed=None,
            cancelled=True,
        )
    return build_ui_response_request(
        ui_request_id=request_id,
        value=answer,
        confirmed=None,
        cancelled=False,
    )


def _editor_ui_response_request(
    event: JsonObject,
    request_id: str,
    read_line: Callable[[str], str],
) -> JsonObject:
    """Build a response request for an editor dialog using line-based input."""

    prefill = event.get("prefill")
    if isinstance(prefill, str) and prefill:
        print("  Current value:")
        for line in prefill.splitlines():
            print(f"    {line}")
    print("  Enter text. Submit with .end on its own line; cancel with .cancel.")

    lines: list[str] = []
    while True:
        line = read_line("  > ")
        if line == ".cancel":
            return build_ui_response_request(
                ui_request_id=request_id,
                value=None,
                confirmed=None,
                cancelled=True,
            )
        if line == ".end":
            return build_ui_response_request(
                ui_request_id=request_id,
                value="\n".join(lines),
                confirmed=None,
                cancelled=False,
            )
        lines.append(line)


async def maybe_interactive_extension_ui_response(
    event: JsonObject,
    *,
    session_id: str,
    interactive_ui: bool,
) -> None:
    """Optionally prompt the user and send an extension UI response."""

    if not interactive_ui or not sys.stdin.isatty():
        return

    response_request = extension_ui_request_to_response(event)
    if response_request is None:
        return
    await request_broker(session_id, response_request)


def parse_confirmed(value: str | None) -> bool | None:
    """Parse optional boolean text for a UI confirm response."""

    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    msg = f"confirmed must be a boolean value, got {value!r}"
    raise ValueError(msg)


def build_ui_response_request(
    *,
    ui_request_id: str,
    value: str | None,
    confirmed: bool | None,
    cancelled: bool,
) -> JsonObject:
    """Build an extension UI response request for the broker."""

    selected_fields = [
        value is not None,
        confirmed is not None,
        cancelled,
    ]
    if sum(selected_fields) != 1:
        msg = "provide exactly one of value, confirmed, or cancelled"
        raise ValueError(msg)

    request: JsonObject = {"type": "ui-response", "uiRequestId": ui_request_id}
    if cancelled:
        request["cancelled"] = True
    elif confirmed is not None:
        request["confirmed"] = confirmed
    else:
        request["value"] = value
    return request

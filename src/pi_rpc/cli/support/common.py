"""Common CLI output and error helpers."""

from __future__ import annotations

import json
import sys
from typing import NoReturn

from pi_rpc.models import SessionStatusView
from pi_rpc.session_id import SessionIdError
from pi_rpc.transport.protocol import JsonObject


def exit_invalid_session(error: SessionIdError) -> NoReturn:
    print(f"Invalid --session-id: {error}", file=sys.stderr)
    raise SystemExit(2)


def print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def print_json_frame(data: object) -> None:
    print(json.dumps(data, sort_keys=True))


def print_text_delta(event: JsonObject) -> None:
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


def broker_status_human(data: dict[str, object]) -> None:
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        print_json(data)
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


def status_human(view: SessionStatusView) -> None:
    print(f"Session: {view.session_id}")
    print(f"Status:  {view.status}")
    print(f"Socket:  {view.socket_path}")
    print(f"PID:     {view.pid_path}")
    print(f"State:   {view.metadata_path}")
    print(f"Log:     {view.log_path}")
    if view.note:
        print(f"Note:    {view.note}")

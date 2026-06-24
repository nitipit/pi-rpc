"""Foreground stateless Pi RPC run helpers."""

from __future__ import annotations

import sys
import tempfile
import uuid
from collections.abc import AsyncIterator, Sequence
from pathlib import Path

from pi_rpc.broker.pi_process import PiRpcProcess
from pi_rpc.cli.support.common import print_json_frame, print_text_delta
from pi_rpc.cli.support.extension_ui import print_extension_ui_request
from pi_rpc.cli.support.payloads import build_prompt_request
from pi_rpc.models import OutputFormat
from pi_rpc.transport.protocol import JsonObject


async def stream_stateless_prompt(
    *,
    message: str,
    image_paths: Sequence[str] | None,
    cwd: str,
    pi_bin: str,
    model: str | None,
    thinking: str | None,
) -> AsyncIterator[JsonObject]:
    """Start one stateless Pi RPC process, send a prompt, and stream frames."""

    log_path = Path(tempfile.gettempdir()) / f"pi-rpc-stateless-{uuid.uuid4().hex}.log"
    process = PiRpcProcess(
        session_id=None,
        cwd=cwd,
        log_path=log_path,
        pi_bin=pi_bin,
        no_session=True,
        model=model,
        thinking=thinking,
    )
    queue: object | None = None
    try:
        await process.start()
        queue = process.subscribe_events()
        response = await process.send_command(
            build_prompt_request(
                message=message,
                streaming_behavior=None,
                image_paths=image_paths,
            )
        )
        yield response
        if not _should_stream_events(response):
            return

        while True:
            event = await queue.get()
            yield event
            if event.get("type") == "agent_end":
                break
    finally:
        if queue is not None:
            process.unsubscribe_events(queue)
        await process.stop()


async def run_stateless_prompt(
    *,
    message: str,
    output: OutputFormat,
    interactive_ui: bool,
    image_paths: Sequence[str] | None,
    cwd: str,
    pi_bin: str,
    model: str | None,
    thinking: str | None,
) -> None:
    """Run a stateless prompt and print output according to CLI format."""

    saw_response = False
    accepted = False
    async for frame in stream_stateless_prompt(
        message=message,
        image_paths=image_paths,
        cwd=cwd,
        pi_bin=pi_bin,
        model=model,
        thinking=thinking,
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
                error = frame.get("error", "run prompt was not accepted")
                print(f"Run failed: {error}", file=sys.stderr)
                raise SystemExit(1)
            continue

        if frame.get("type") == "agent_end":
            print()

        print_extension_ui_request(frame, session_id=None, manual_hint=False)
        if interactive_ui and sys.stdin.isatty() and frame.get("type") == "extension_ui_request":
            print("  stateless run cannot answer extension UI requests yet")
        print_text_delta(frame)

    if not saw_response:
        print("No run response from Pi RPC process.", file=sys.stderr)
        raise SystemExit(1)
    if output == "human" and not accepted:
        raise SystemExit(1)


def _should_stream_events(response: JsonObject) -> bool:
    return (
        response.get("type") == "response"
        and response.get("command") == "prompt"
        and response.get("success") is True
    )

"""Detached job worker entrypoint."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

from pi_rpc.broker.pi_process import PiRpcProcess
from pi_rpc.client.broker import stream_broker
from pi_rpc.jobs.manager import (
    append_job_frame,
    read_job_request,
    update_job_status,
)
from pi_rpc.paths import paths_for_job
from pi_rpc.transport.protocol import JsonObject


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one detached pi-rpc job.")
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    try:
        asyncio.run(run_job(args.job_id))
    except Exception as exc:
        update_job_status(args.job_id, status="failed", error=str(exc), exit_code=1)
        raise


async def run_job(job_id: str) -> None:
    """Run one detached job and persist frames."""

    request = read_job_request(job_id)
    kind = request.get("kind")
    try:
        if kind == "stateless-run":
            await _run_stateless(job_id, request)
        elif kind == "stateful-prompt":
            await _run_stateful_prompt(job_id, request)
        else:
            msg = f"unsupported job kind: {kind!r}"
            raise ValueError(msg)
    except Exception as exc:
        update_job_status(job_id, status="failed", error=str(exc), exit_code=1)
        return
    update_job_status(job_id, status="succeeded", exit_code=0)


async def _run_stateful_prompt(job_id: str, request: dict[str, Any]) -> None:
    session_id = request.get("sessionId")
    prompt_request = request.get("promptRequest")
    if not isinstance(session_id, str) or not isinstance(prompt_request, dict):
        msg = "stateful prompt job requires sessionId and promptRequest"
        raise ValueError(msg)
    async for frame in stream_broker(session_id, prompt_request):
        append_job_frame(job_id, frame)
        if frame.get("type") == "agent_end":
            break


async def _run_stateless(job_id: str, request: dict[str, Any]) -> None:
    prompt_request = request.get("promptRequest")
    if not isinstance(prompt_request, dict):
        msg = "stateless run job requires promptRequest"
        raise ValueError(msg)
    paths = paths_for_job(job_id)
    process = PiRpcProcess(
        session_id=None,
        cwd=str(request.get("cwd") or Path.cwd()),
        log_path=paths.log_path,
        pi_bin=str(request.get("piBin") or "pi"),
        no_session=True,
        model=_string_or_none(request.get("model")),
        thinking=_string_or_none(request.get("thinking")),
    )
    queue = None
    try:
        await process.start()
        queue = process.subscribe_events()
        response = await process.send_command(dict(prompt_request))
        append_job_frame(job_id, response)
        if not _should_stream_events(response):
            return
        while True:
            event = await queue.get()
            append_job_frame(job_id, event)
            if event.get("type") == "agent_end":
                break
    finally:
        if queue is not None:
            process.unsubscribe_events(queue)
        await process.stop()


def _should_stream_events(response: JsonObject) -> bool:
    return (
        response.get("type") == "response"
        and response.get("command") == "prompt"
        and response.get("success") is True
    )


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


if __name__ == "__main__":
    main()

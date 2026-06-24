"""Detached job creation and inspection."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pi_rpc.cli.support.payloads import build_prompt_request
from pi_rpc.jobs.models import JobKind, JobRecord, JobStatus
from pi_rpc.paths import known_job_metadata_paths, paths_for_job
from pi_rpc.session_id import session_identity
from pi_rpc.transport.protocol import JsonObject, decode_jsonl_line, encode_jsonl


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""

    return datetime.now(UTC).isoformat()


def new_job_id() -> str:
    """Create a readable unique job id."""

    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"job-{stamp}-{uuid.uuid4().hex[:8]}"


def start_stateless_run_job(
    *,
    message: str,
    image_paths: Sequence[str] | None,
    cwd: str,
    pi_bin: str,
    model: str | None,
    thinking: str | None,
) -> JobRecord:
    """Create and launch a detached stateless run job."""

    job_id = new_job_id()
    request: JsonObject = {
        "kind": "stateless-run",
        "message": message,
        "promptRequest": build_prompt_request(
            message=message,
            streaming_behavior=None,
            image_paths=image_paths,
        ),
        "cwd": cwd,
        "piBin": pi_bin,
        "model": model,
        "thinking": thinking,
        "sessionId": None,
    }
    return _start_job(job_id=job_id, kind="stateless-run", request=request)


def start_stateful_prompt_job(
    *,
    session_id: str,
    message: str,
    image_paths: Sequence[str] | None,
    streaming_behavior: str | None,
) -> JobRecord:
    """Create and launch a detached prompt job against an existing session broker."""

    identity = session_identity(session_id)
    job_id = new_job_id()
    request: JsonObject = {
        "kind": "stateful-prompt",
        "message": message,
        "promptRequest": build_prompt_request(
            message=message,
            streaming_behavior=streaming_behavior,
            image_paths=image_paths,
        ),
        "sessionId": identity.value,
    }
    return _start_job(job_id=job_id, kind="stateful-prompt", request=request)


def _start_job(*, job_id: str, kind: JobKind, request: JsonObject) -> JobRecord:
    paths = paths_for_job(job_id)
    paths.request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
    now = utc_now_iso()
    record = JobRecord(
        job_id=job_id,
        kind=kind,
        status="queued",
        created_at=now,
        updated_at=now,
        pid=None,
        session_id=_string_or_none(request.get("sessionId")),
        message=str(request.get("message", "")),
        metadata_path=str(paths.metadata_path),
        request_path=str(paths.request_path),
        frames_path=str(paths.frames_path),
        log_path=str(paths.log_path),
    )
    write_job_record(record)
    process = subprocess.Popen(
        [sys.executable, "-m", "pi_rpc.jobs.worker", "--job-id", job_id],
        cwd=Path.cwd(),
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    record = JobRecord(
        job_id=record.job_id,
        kind=record.kind,
        status="running",
        created_at=record.created_at,
        updated_at=utc_now_iso(),
        pid=process.pid,
        session_id=record.session_id,
        message=record.message,
        metadata_path=record.metadata_path,
        request_path=record.request_path,
        frames_path=record.frames_path,
        log_path=record.log_path,
        error=record.error,
        exit_code=record.exit_code,
    )
    write_job_record(record)
    paths.pid_path.write_text(str(process.pid), encoding="utf-8")
    return record


def write_job_record(record: JobRecord) -> None:
    """Write job metadata."""

    paths = paths_for_job(record.job_id)
    paths.metadata_path.write_text(
        json.dumps(record.as_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )


def read_job_record(job_id: str) -> JobRecord:
    """Read one job metadata record."""

    path = paths_for_job(job_id).metadata_path
    data = json.loads(path.read_text(encoding="utf-8"))
    return JobRecord(**data)


def list_job_records() -> list[JobRecord]:
    """List known detached jobs."""

    records: list[JobRecord] = []
    for path in known_job_metadata_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            records.append(JobRecord(**data))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return sorted(records, key=lambda record: record.created_at)


def read_job_frames(job_id: str) -> list[JsonObject]:
    """Read stored JSONL frames for a job."""

    path = paths_for_job(job_id).frames_path
    if not path.exists():
        return []
    frames: list[JsonObject] = []
    with path.open("rb") as frame_file:
        for line in frame_file:
            if line.strip():
                frames.append(decode_jsonl_line(line))
    return frames


def append_job_frame(job_id: str, frame: JsonObject) -> None:
    """Append one frame to a job's JSONL result log."""

    paths = paths_for_job(job_id)
    with paths.frames_path.open("ab") as frame_file:
        frame_file.write(encode_jsonl(frame))


def job_text(frames: Sequence[JsonObject]) -> str:
    """Return concatenated assistant text deltas from job frames."""

    parts: list[str] = []
    for frame in frames:
        if frame.get("type") != "message_update":
            continue
        event = frame.get("assistantMessageEvent")
        if isinstance(event, dict) and event.get("type") == "text_delta":
            delta = event.get("delta")
            if isinstance(delta, str):
                parts.append(delta)
    return "".join(parts)


def update_job_status(
    job_id: str,
    *,
    status: JobStatus,
    error: str | None = None,
    exit_code: int | None = None,
) -> None:
    """Update job status fields."""

    record = read_job_record(job_id)
    write_job_record(
        JobRecord(
            job_id=record.job_id,
            kind=record.kind,
            status=status,
            created_at=record.created_at,
            updated_at=utc_now_iso(),
            pid=record.pid,
            session_id=record.session_id,
            message=record.message,
            metadata_path=record.metadata_path,
            request_path=record.request_path,
            frames_path=record.frames_path,
            log_path=record.log_path,
            error=error,
            exit_code=exit_code,
        )
    )


def read_job_request(job_id: str) -> dict[str, Any]:
    """Read a job request payload."""

    return json.loads(paths_for_job(job_id).request_path.read_text(encoding="utf-8"))


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None

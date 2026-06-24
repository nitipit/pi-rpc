from __future__ import annotations

import json
from pathlib import Path

from pi_rpc.broker.pi_process import PiRpcProcess
from pi_rpc.jobs.manager import job_text, read_job_frames
from pi_rpc.paths import paths_for_job
from pi_rpc.transport.protocol import encode_jsonl


def test_pi_rpc_process_builds_no_session_command(tmp_path: Path) -> None:
    process = PiRpcProcess(
        session_id=None,
        cwd=str(tmp_path),
        log_path=tmp_path / "pi.log",
        pi_bin="pi",
        no_session=True,
        model="openai/example",
        thinking="low",
    )

    assert process._command() == [
        "pi",
        "--mode",
        "rpc",
        "--no-session",
        "--model",
        "openai/example",
        "--thinking",
        "low",
    ]


def test_pi_rpc_process_builds_session_command(tmp_path: Path) -> None:
    process = PiRpcProcess(
        session_id="dev",
        cwd=str(tmp_path),
        log_path=tmp_path / "pi.log",
        pi_bin="pi",
        name="Dev Session",
    )

    assert process._command() == [
        "pi",
        "--mode",
        "rpc",
        "--session-id",
        "dev",
        "--name",
        "Dev Session",
    ]


def test_job_text_collects_text_deltas() -> None:
    assert (
        job_text(
            [
                {"type": "response", "success": True},
                {
                    "type": "message_update",
                    "assistantMessageEvent": {"type": "text_delta", "delta": "Hello "},
                },
                {
                    "type": "message_update",
                    "assistantMessageEvent": {"type": "text_delta", "delta": "world"},
                },
            ]
        )
        == "Hello world"
    )


def test_read_job_frames(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))
    paths = paths_for_job("job-test")
    paths.frames_path.write_bytes(
        encode_jsonl({"type": "response", "success": True})
        + encode_jsonl({"type": "agent_end", "messages": []})
    )

    assert read_job_frames("job-test") == [
        {"type": "response", "success": True},
        {"type": "agent_end", "messages": []},
    ]


def test_paths_for_job_creates_distinct_state_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path / "runtime"))

    paths = paths_for_job("job-test")

    assert paths.pid_path.name == "job-test.pid"
    assert paths.metadata_path.name == "job-test.json"
    assert paths.request_path.name == "job-test.request.json"
    assert paths.frames_path.name == "job-test.frames.jsonl"
    assert paths.log_path.name == "job-test.log"
    assert json.loads(json.dumps(paths.as_dict()))["job_id"] == "job-test"

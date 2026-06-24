"""Platform-aware local paths for pi-rpc runtime and state files."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_runtime_path, user_state_path

from pi_rpc.session_id import SessionIdentity, session_identity

APP_NAME = "pi-rpc"


@dataclass(frozen=True)
class AppPaths:
    """Base directories used by pi-rpc."""

    runtime_dir: Path
    state_dir: Path


@dataclass(frozen=True)
class JobPaths:
    """Local runtime and state paths for one detached job."""

    job_id: str
    pid_path: Path
    metadata_path: Path
    request_path: Path
    frames_path: Path
    log_path: Path

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-friendly representation."""

        data = asdict(self)
        return {key: str(value) for key, value in data.items()}


@dataclass(frozen=True)
class SessionPaths:
    """Local runtime and state paths for one session id."""

    session_id: str
    file_stem: str
    socket_path: Path
    pid_path: Path
    metadata_path: Path
    log_path: Path

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-friendly representation."""

        data = asdict(self)
        return {key: str(value) for key, value in data.items()}


def app_paths(*, ensure_exists: bool = True) -> AppPaths:
    """Return platform-specific base paths for runtime and durable state."""

    runtime_dir = user_runtime_path(APP_NAME, ensure_exists=ensure_exists)
    state_dir = user_state_path(APP_NAME, ensure_exists=ensure_exists)
    return AppPaths(runtime_dir=runtime_dir, state_dir=state_dir)


def paths_for_job(job_id: str, *, ensure_exists: bool = True) -> JobPaths:
    """Return all local paths for a detached job id."""

    if not job_id or not all(char.isalnum() or char in {"-", "_"} for char in job_id):
        msg = f"invalid job id: {job_id!r}"
        raise ValueError(msg)
    paths = app_paths(ensure_exists=ensure_exists)
    runtime_job_dir = paths.runtime_dir / "jobs"
    state_job_dir = paths.state_dir / "jobs"
    if ensure_exists:
        runtime_job_dir.mkdir(parents=True, exist_ok=True)
        state_job_dir.mkdir(parents=True, exist_ok=True)

    return JobPaths(
        job_id=job_id,
        pid_path=runtime_job_dir / f"{job_id}.pid",
        metadata_path=state_job_dir / f"{job_id}.json",
        request_path=state_job_dir / f"{job_id}.request.json",
        frames_path=state_job_dir / f"{job_id}.frames.jsonl",
        log_path=state_job_dir / f"{job_id}.log",
    )


def paths_for_session(session_id: str, *, ensure_exists: bool = True) -> SessionPaths:
    """Return all local paths for a validated session id."""

    identity: SessionIdentity = session_identity(session_id)
    paths = app_paths(ensure_exists=ensure_exists)
    runtime_session_dir = paths.runtime_dir / "sessions"
    state_session_dir = paths.state_dir / "sessions"
    if ensure_exists:
        runtime_session_dir.mkdir(parents=True, exist_ok=True)
        state_session_dir.mkdir(parents=True, exist_ok=True)

    stem = identity.file_stem
    return SessionPaths(
        session_id=identity.value,
        file_stem=stem,
        socket_path=runtime_session_dir / f"{stem}.sock",
        pid_path=runtime_session_dir / f"{stem}.pid",
        metadata_path=state_session_dir / f"{stem}.json",
        log_path=state_session_dir / f"{stem}.log",
    )


def known_job_metadata_paths(*, ensure_exists: bool = True) -> list[Path]:
    """Return known detached job metadata files sorted by name."""

    state_job_dir = app_paths(ensure_exists=ensure_exists).state_dir / "jobs"
    if ensure_exists:
        state_job_dir.mkdir(parents=True, exist_ok=True)
    if not state_job_dir.exists():
        return []
    return sorted(state_job_dir.glob("*.json"))


def known_metadata_paths(*, ensure_exists: bool = True) -> list[Path]:
    """Return known pi-rpc metadata files sorted by name."""

    state_session_dir = app_paths(ensure_exists=ensure_exists).state_dir / "sessions"
    if ensure_exists:
        state_session_dir.mkdir(parents=True, exist_ok=True)
    if not state_session_dir.exists():
        return []
    return sorted(state_session_dir.glob("*.json"))

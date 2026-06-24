"""Detached job records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

JobKind = Literal["stateless-run", "stateful-prompt"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]


@dataclass(frozen=True)
class JobRecord:
    """Stored metadata for one detached job."""

    job_id: str
    kind: JobKind
    status: JobStatus
    created_at: str
    updated_at: str
    pid: int | None
    session_id: str | None
    message: str
    metadata_path: str
    request_path: str
    frames_path: str
    log_path: str
    error: str | None = None
    exit_code: int | None = None

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""

        return asdict(self)

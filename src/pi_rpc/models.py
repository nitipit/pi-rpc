"""Shared data models for pi-rpc."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

SessionStatus = Literal["running", "stopped", "stale", "unknown"]
OutputFormat = Literal["human", "json"]


@dataclass(frozen=True)
class SessionStatusView:
    """User-facing status snapshot for one managed Pi RPC session."""

    session_id: str
    status: SessionStatus
    socket_path: str
    pid_path: str
    metadata_path: str
    log_path: str
    note: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        """Return a JSON-friendly dictionary."""

        return asdict(self)

"""Broker metadata persisted for client discovery and status."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BrokerMetadata:
    """Durable description of a running or recently running broker."""

    session_id: str
    broker_pid: int
    pi_pid: int | None
    socket_path: str
    pid_path: str
    metadata_path: str
    log_path: str
    cwd: str
    name: str | None
    started_at: str
    pi_ready: bool = False
    status: str = "running"

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        return asdict(self)


def utc_now_iso() -> str:
    """Return the current UTC timestamp for metadata."""
    return datetime.now(UTC).isoformat()


def write_metadata(metadata: BrokerMetadata) -> None:
    """Write broker metadata atomically enough for local status usage."""
    path = Path(metadata.metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(metadata.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def read_metadata(path: str | Path) -> dict[str, Any] | None:
    """Read broker metadata, returning ``None`` when absent or invalid."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None

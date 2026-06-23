"""Validation and filesystem-safe names for Pi session ids."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
MAX_SESSION_ID_LENGTH = 128


class SessionIdError(ValueError):
    """Raised when a session id cannot be used by pi-rpc."""


@dataclass(frozen=True)
class SessionIdentity:
    """A validated Pi session id and its safe local file stem."""

    value: str
    file_stem: str


def validate_session_id(session_id: str) -> str:
    """Return a valid session id or raise :class:`SessionIdError`.

    pi-rpc treats ``--session-id`` as a readable, stable handle. Keep it easy to
    type in terminals and safe to use in local runtime paths.
    """

    if not session_id:
        msg = "session id is required"
        raise SessionIdError(msg)
    if len(session_id) > MAX_SESSION_ID_LENGTH:
        msg = f"session id must be {MAX_SESSION_ID_LENGTH} characters or fewer"
        raise SessionIdError(msg)
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        msg = "session id may contain only letters, numbers, dots, underscores, and dashes"
        raise SessionIdError(msg)
    if session_id in {".", ".."}:
        msg = "session id cannot be '.' or '..'"
        raise SessionIdError(msg)
    return session_id


def session_file_stem(session_id: str) -> str:
    """Return a short path-safe stem for a validated session id."""

    value = validate_session_id(session_id)
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    slug = value[:48].strip(".") or "session"
    return f"{slug}-{digest}"


def session_identity(session_id: str) -> SessionIdentity:
    """Return the validated identity used across local pi-rpc state."""

    value = validate_session_id(session_id)
    return SessionIdentity(value=value, file_stem=session_file_stem(value))

"""JSONL envelope helpers for pi-rpc client-to-broker messages."""

from __future__ import annotations

import json
from typing import Any

JsonObject = dict[str, Any]


class ProtocolError(ValueError):
    """Raised when a pi-rpc transport frame is invalid."""


def encode_jsonl(message: JsonObject) -> bytes:
    """Serialize one JSON object as a UTF-8 JSONL frame."""

    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode_jsonl_line(line: bytes) -> JsonObject:
    """Decode one UTF-8 JSONL frame into a JSON object."""

    if line.endswith(b"\n"):
        line = line[:-1]
    if line.endswith(b"\r"):
        line = line[:-1]
    try:
        value = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = f"invalid JSONL frame: {exc}"
        raise ProtocolError(msg) from exc
    if not isinstance(value, dict):
        msg = "JSONL frame must decode to an object"
        raise ProtocolError(msg)
    return value

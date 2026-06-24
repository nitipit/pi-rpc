"""Dictify schemas for broker control messages."""

from __future__ import annotations

from typing import Annotated, Any, Literal, cast

from dictify import Field, Model

BrokerRequestType = Literal[
    "ping",
    "status",
    "shutdown",
    "prompt",
    "steer",
    "follow_up",
    "abort",
    "bash",
    "abort_bash",
    "state",
    "models",
    "stats",
    "messages",
    "last-assistant-text",
    "commands",
    "model",
    "cycle-model",
    "thinking",
    "cycle-thinking",
    "name",
    "compact",
    "auto-compaction",
    "auto-retry",
    "steering-mode",
    "follow-up-mode",
    "abort-retry",
    "new-session",
    "switch-session",
    "clone",
    "fork",
    "fork-messages",
    "export-html",
]
BROKER_REQUEST_TYPES = {
    "ping",
    "status",
    "shutdown",
    "prompt",
    "steer",
    "follow_up",
    "abort",
    "bash",
    "abort_bash",
    "state",
    "models",
    "stats",
    "messages",
    "last-assistant-text",
    "commands",
    "model",
    "cycle-model",
    "thinking",
    "cycle-thinking",
    "name",
    "compact",
    "auto-compaction",
    "auto-retry",
    "steering-mode",
    "follow-up-mode",
    "abort-retry",
    "new-session",
    "switch-session",
    "clone",
    "fork",
    "fork-messages",
    "export-html",
}
PASS_THROUGH_REQUEST_TYPES = {
    "prompt",
    "steer",
    "follow_up",
    "abort",
    "bash",
    "abort_bash",
    "state",
    "models",
    "stats",
    "messages",
    "last-assistant-text",
    "commands",
    "model",
    "cycle-model",
    "thinking",
    "cycle-thinking",
    "name",
    "compact",
    "auto-compaction",
    "auto-retry",
    "steering-mode",
    "follow-up-mode",
    "abort-retry",
    "new-session",
    "switch-session",
    "clone",
    "fork",
    "fork-messages",
    "export-html",
}


def is_broker_request_type(value: str) -> bool:
    """Return whether a value is a supported broker request type."""
    return value in BROKER_REQUEST_TYPES


class BrokerSchemaError(ValueError):
    """Raised when a broker protocol message fails validation."""


class BrokerRequest(Model):
    """Validated client-to-broker lifecycle request."""

    type: Annotated[
        str,
        Field(required=True).verify(is_broker_request_type, "unsupported broker request type"),
    ]


def validate_broker_request(message: dict[str, Any]) -> BrokerRequestType:
    """Validate a broker request and return its request type."""
    request_type = message.get("type") if isinstance(message, dict) else None
    if request_type in PASS_THROUGH_REQUEST_TYPES:
        return cast("BrokerRequestType", request_type)

    try:
        request = BrokerRequest(message)
    except Model.Error as exc:
        msg = f"invalid broker request: {exc}"
        raise BrokerSchemaError(msg) from exc

    request_type = request["type"]
    assert request_type in BROKER_REQUEST_TYPES
    return cast("BrokerRequestType", request_type)

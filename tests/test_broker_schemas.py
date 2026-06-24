from __future__ import annotations

import pytest

from pi_rpc.broker.schemas import BrokerSchemaError, validate_broker_request


@pytest.mark.parametrize(
    "request_type",
    [
        "ping",
        "status",
        "shutdown",
        "prompt",
        "steer",
        "follow_up",
        "abort",
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
        "bash",
        "abort_bash",
        "ui-response",
        "new-session",
        "switch-session",
        "clone",
        "fork",
        "fork-messages",
        "export-html",
    ],
)
def test_validate_broker_request_accepts_known_types(request_type: str) -> None:
    assert validate_broker_request({"type": request_type}) == request_type


@pytest.mark.parametrize("message", [{}, {"type": 1}])
def test_validate_broker_request_rejects_invalid_messages(message: dict[str, object]) -> None:
    with pytest.raises(BrokerSchemaError):
        validate_broker_request(message)


def test_validate_broker_request_accepts_pass_through_payloads() -> None:
    assert (
        validate_broker_request(
            {
                "type": "prompt",
                "message": "Hi",
                "images": [{"type": "image", "data": "x", "mimeType": "text/plain"}],
                "streamingBehavior": "steer",
            }
        )
        == "prompt"
    )
    assert validate_broker_request({"type": "steer", "message": "Adjust this"}) == "steer"
    assert validate_broker_request({"type": "follow_up", "message": "Then do that"}) == "follow_up"
    assert validate_broker_request({"type": "abort"}) == "abort"
    assert validate_broker_request({"type": "state"}) == "state"
    assert validate_broker_request({"type": "models"}) == "models"
    assert validate_broker_request({"type": "stats"}) == "stats"
    assert validate_broker_request({"type": "messages"}) == "messages"
    assert validate_broker_request({"type": "last-assistant-text"}) == "last-assistant-text"
    assert validate_broker_request({"type": "commands"}) == "commands"
    assert validate_broker_request({"type": "model"}) == "model"
    assert validate_broker_request({"type": "cycle-model"}) == "cycle-model"
    assert validate_broker_request({"type": "thinking"}) == "thinking"
    assert validate_broker_request({"type": "cycle-thinking"}) == "cycle-thinking"
    assert validate_broker_request({"type": "name", "name": "New name"}) == "name"
    assert (
        validate_broker_request({"type": "compact", "customInstructions": "compress now"})
        == "compact"
    )
    assert (
        validate_broker_request({"type": "auto-compaction", "enabled": False}) == "auto-compaction"
    )
    assert validate_broker_request({"type": "auto-retry", "enabled": True}) == "auto-retry"
    assert validate_broker_request({"type": "steering-mode", "mode": "all"}) == "steering-mode"
    assert (
        validate_broker_request({"type": "follow-up-mode", "mode": "one-at-a-time"})
        == "follow-up-mode"
    )
    assert validate_broker_request({"type": "abort-retry"}) == "abort-retry"
    assert validate_broker_request({"type": "bash", "command": "ls"}) == "bash"
    assert validate_broker_request({"type": "abort_bash"}) == "abort_bash"
    assert (
        validate_broker_request({"type": "ui-response", "uiRequestId": "ui-1", "value": "ok"})
        == "ui-response"
    )
    assert (
        validate_broker_request({"type": "new-session", "parentSession": "/tmp/session.json"})
        == "new-session"
    )
    assert (
        validate_broker_request({"type": "switch-session", "sessionPath": "/tmp/session.json"})
        == "switch-session"
    )
    assert validate_broker_request({"type": "clone"}) == "clone"
    assert validate_broker_request({"type": "fork", "entryId": "entry-1"}) == "fork"
    assert validate_broker_request({"type": "fork-messages"}) == "fork-messages"
    assert (
        validate_broker_request({"type": "export-html", "outputPath": "/tmp/out.html"})
        == "export-html"
    )

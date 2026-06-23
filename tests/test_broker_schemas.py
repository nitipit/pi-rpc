from __future__ import annotations

import pytest

from pi_rpc.broker.schemas import BrokerSchemaError, validate_broker_request


@pytest.mark.parametrize(
    "request_type", ["ping", "status", "shutdown", "prompt", "steer", "follow_up", "abort"]
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

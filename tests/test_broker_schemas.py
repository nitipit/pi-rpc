from __future__ import annotations

import pytest

from pi_rpc.broker.schemas import BrokerSchemaError, validate_broker_request


@pytest.mark.parametrize("request_type", ["ping", "status", "shutdown"])
def test_validate_broker_request_accepts_known_types(request_type: str) -> None:
    assert validate_broker_request({"type": request_type}) == request_type


@pytest.mark.parametrize("message", [{}, {"type": "prompt"}, {"type": 1}])
def test_validate_broker_request_rejects_invalid_messages(message: dict[str, object]) -> None:
    with pytest.raises(BrokerSchemaError):
        validate_broker_request(message)

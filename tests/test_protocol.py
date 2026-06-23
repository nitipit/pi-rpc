from __future__ import annotations

import pytest

from pi_rpc.transport.protocol import ProtocolError, decode_jsonl_line, encode_jsonl


def test_encode_decode_jsonl_round_trip() -> None:
    payload = {"type": "status", "session_id": "pi-rpc-dev"}

    encoded = encode_jsonl(payload)

    assert encoded.endswith(b"\n")
    assert decode_jsonl_line(encoded) == payload


def test_decode_jsonl_accepts_crlf() -> None:
    assert decode_jsonl_line(b'{"type":"ok"}\r\n') == {"type": "ok"}


def test_decode_jsonl_rejects_non_object() -> None:
    with pytest.raises(ProtocolError):
        decode_jsonl_line(b"[]\n")

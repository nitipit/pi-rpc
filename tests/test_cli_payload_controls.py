from __future__ import annotations

import base64

import pytest

from pi_rpc.cli import (
    _build_bash_request,
    _build_image_payloads,
    _build_message_request,
    _build_prompt_request,
)


def test_prompt_request_omits_streaming_behavior_by_default() -> None:
    assert _build_prompt_request(message="hello", streaming_behavior=None, image_paths=None) == {
        "type": "prompt",
        "message": "hello",
    }


def test_prompt_request_adds_streaming_behavior() -> None:
    assert _build_prompt_request(
        message="hello",
        streaming_behavior="steer",
        image_paths=None,
    ) == {
        "type": "prompt",
        "message": "hello",
        "streamingBehavior": "steer",
    }


def test_prompt_request_adds_images(tmp_path) -> None:
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"png-bytes")

    request = _build_prompt_request(
        message="describe",
        streaming_behavior=None,
        image_paths=[str(image_path)],
    )

    assert request == {
        "type": "prompt",
        "message": "describe",
        "images": [
            {
                "type": "image",
                "data": base64.b64encode(b"png-bytes").decode("ascii"),
                "mimeType": "image/png",
            }
        ],
    }


def test_message_request_adds_images(tmp_path) -> None:
    image_path = tmp_path / "sample.jpeg"
    image_path.write_bytes(b"jpeg-bytes")

    request = _build_message_request(
        command="steer",
        message="look here",
        image_paths=[str(image_path)],
    )

    assert request == {
        "type": "steer",
        "message": "look here",
        "images": [
            {
                "type": "image",
                "data": base64.b64encode(b"jpeg-bytes").decode("ascii"),
                "mimeType": "image/jpeg",
            }
        ],
    }


def test_image_payload_rejects_non_image_extension(tmp_path) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("not an image", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported image type"):
        _build_image_payloads([str(text_path)])


def test_image_payload_reports_missing_file() -> None:
    with pytest.raises(ValueError, match="Unable to read image"):
        _build_image_payloads(["missing.png"])


def test_bash_request_omits_exclude_from_context_by_default() -> None:
    assert _build_bash_request(command="git status", exclude_from_context=False) == {
        "type": "bash",
        "command": "git status",
    }


def test_bash_request_adds_exclude_from_context() -> None:
    assert _build_bash_request(command="git status", exclude_from_context=True) == {
        "type": "bash",
        "command": "git status",
        "excludeFromContext": True,
    }

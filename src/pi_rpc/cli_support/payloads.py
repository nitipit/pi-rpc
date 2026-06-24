"""Request payload builders for CLI commands."""

from __future__ import annotations

import base64
import mimetypes
from collections.abc import Sequence
from pathlib import Path

from pi_rpc.transport.protocol import JsonObject

StreamingBehavior = str


def build_prompt_request(
    *,
    message: str,
    streaming_behavior: StreamingBehavior | None,
    image_paths: Sequence[str] | None,
) -> JsonObject:
    """Build a prompt request for the broker or direct Pi RPC process."""

    request = build_message_request(
        command="prompt",
        message=message,
        image_paths=image_paths,
    )
    if streaming_behavior is not None:
        request["streamingBehavior"] = streaming_behavior
    return request


def build_message_request(
    *,
    command: str,
    message: str | None,
    image_paths: Sequence[str] | None,
) -> JsonObject:
    """Build a message-style request with optional images."""

    request: JsonObject = {"type": command}
    if message is not None:
        request["message"] = message
    images = build_image_payloads(image_paths)
    if images:
        request["images"] = images
    return request


def build_image_payloads(image_paths: Sequence[str] | None) -> list[JsonObject]:
    """Load image files into Pi RPC ImageContent payloads."""

    if not image_paths:
        return []
    return [_build_image_payload(path_text) for path_text in image_paths]


def _build_image_payload(path_text: str) -> JsonObject:
    """Load one image file into a Pi RPC ImageContent payload."""

    path = Path(path_text).expanduser()
    mime_type = mimetypes.guess_type(str(path))[0]
    if mime_type is None or not mime_type.startswith("image/"):
        msg = f"Unsupported image type for {path}. Use a file with an image MIME type."
        raise ValueError(msg)
    try:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError as exc:
        msg = f"Unable to read image {path}: {exc}"
        raise ValueError(msg) from exc
    return {"type": "image", "data": data, "mimeType": mime_type}


def build_bash_request(*, command: str, exclude_from_context: bool) -> JsonObject:
    """Build a bash request for the broker."""

    request: JsonObject = {"type": "bash", "command": command}
    if exclude_from_context:
        request["excludeFromContext"] = True
    return request

from __future__ import annotations

from collections.abc import Iterator

from pi_rpc.cli import _extension_ui_request_to_response


def _reader(*answers: str):
    iterator: Iterator[str] = iter(answers)

    def read_line(_prompt: str) -> str:
        return next(iterator)

    return read_line


def test_select_ui_response_accepts_option_number() -> None:
    request = _extension_ui_request_to_response(
        {
            "type": "extension_ui_request",
            "id": "ui-1",
            "method": "select",
            "title": "Choose",
            "options": ["Allow", "Block"],
        },
        read_line=_reader("2"),
    )

    assert request == {"type": "ui-response", "uiRequestId": "ui-1", "value": "Block"}


def test_select_ui_response_can_cancel() -> None:
    request = _extension_ui_request_to_response(
        {
            "type": "extension_ui_request",
            "id": "ui-1",
            "method": "select",
            "options": ["Allow", "Block"],
        },
        read_line=_reader("/cancel"),
    )

    assert request == {"type": "ui-response", "uiRequestId": "ui-1", "cancelled": True}


def test_confirm_ui_response_accepts_no() -> None:
    request = _extension_ui_request_to_response(
        {"type": "extension_ui_request", "id": "ui-2", "method": "confirm"},
        read_line=_reader("n"),
    )

    assert request == {"type": "ui-response", "uiRequestId": "ui-2", "confirmed": False}


def test_input_ui_response_keeps_empty_value() -> None:
    request = _extension_ui_request_to_response(
        {"type": "extension_ui_request", "id": "ui-3", "method": "input"},
        read_line=_reader(""),
    )

    assert request == {"type": "ui-response", "uiRequestId": "ui-3", "value": ""}


def test_editor_ui_response_collects_lines_until_end() -> None:
    request = _extension_ui_request_to_response(
        {"type": "extension_ui_request", "id": "ui-4", "method": "editor"},
        read_line=_reader("line 1", "line 2", ".end"),
    )

    assert request == {"type": "ui-response", "uiRequestId": "ui-4", "value": "line 1\nline 2"}


def test_non_dialog_ui_request_has_no_response() -> None:
    request = _extension_ui_request_to_response(
        {"type": "extension_ui_request", "id": "ui-5", "method": "notify"},
        read_line=_reader(),
    )

    assert request is None


def test_malformed_ui_method_has_no_response() -> None:
    request = _extension_ui_request_to_response(
        {"type": "extension_ui_request", "id": "ui-6", "method": ["select"]},
        read_line=_reader(),
    )

    assert request is None

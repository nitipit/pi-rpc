from __future__ import annotations

from pi_rpc.cli import _build_bash_request, _build_prompt_request


def test_prompt_request_omits_streaming_behavior_by_default() -> None:
    assert _build_prompt_request(message="hello", streaming_behavior=None) == {
        "type": "prompt",
        "message": "hello",
    }


def test_prompt_request_adds_streaming_behavior() -> None:
    assert _build_prompt_request(message="hello", streaming_behavior="steer") == {
        "type": "prompt",
        "message": "hello",
        "streamingBehavior": "steer",
    }


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

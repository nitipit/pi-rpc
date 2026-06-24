from __future__ import annotations

import pytest

from pi_rpc.cli import (
    _extract_model_refs,
    _print_abort_bash_summary,
    _print_bash_summary,
    _resolve_model_from_available_models,
)


def test_extract_model_refs_from_pi_model_objects() -> None:
    assert _extract_model_refs(
        {
            "models": [
                {"provider": "openai", "id": "gpt-4"},
                {"provider": "google", "id": "gemini-pro"},
            ]
        }
    ) == ["openai/gpt-4", "google/gemini-pro"]


def test_resolve_model_exact_provider_id_match() -> None:
    assert (
        _resolve_model_from_available_models(
            available=["openai/gpt-4", "google/gemini-pro"], requested_model="openai/gpt-4"
        )
        == "openai/gpt-4"
    )


def test_resolve_model_unique_bare_id_match() -> None:
    assert (
        _resolve_model_from_available_models(
            available=["openai/gpt-4", "google/gemini-pro"],
            requested_model="gemini-pro",
        )
        == "google/gemini-pro"
    )


def test_resolve_model_unknown_bare_id() -> None:
    with pytest.raises(ValueError, match="Unknown model"):
        _resolve_model_from_available_models(
            available=["openai/gpt-4", "google/gemini-pro"], requested_model="missing"
        )


def test_resolve_model_ambiguous_bare_id() -> None:
    with pytest.raises(ValueError, match="Ambiguous"):
        _resolve_model_from_available_models(
            available=["openai/gpt-4", "google/gpt-4"], requested_model="gpt-4"
        )


def test_print_bash_summary_human(capsys: pytest.CaptureFixture[str]) -> None:
    response = {
        "data": {
            "exitCode": 0,
            "cancelled": False,
            "truncated": False,
            "output": "hello from bash",
        }
    }
    _print_bash_summary(response)

    expected = [
        "  exitCode: 0",
        "  cancelled: False",
        "  truncated: False",
        "  output: hello from bash",
    ]
    assert capsys.readouterr().out.splitlines() == expected


def test_print_bash_summary_path_fallback(capsys: pytest.CaptureFixture[str]) -> None:
    response = {"data": {"exitCode": 1, "outputPath": "/tmp/output.txt"}}
    _print_bash_summary(response)

    assert capsys.readouterr().out.splitlines() == ["  exitCode: 1", "  path: /tmp/output.txt"]


def test_print_abort_bash_summary(capsys: pytest.CaptureFixture[str]) -> None:
    response = {"data": {"aborted": False}}
    _print_abort_bash_summary(response)

    assert capsys.readouterr().out.rstrip("\n") == "  abort-bash: nothing to abort"

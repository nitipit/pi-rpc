from __future__ import annotations

import pytest

from pi_rpc.cli import _extract_model_refs, _resolve_model_from_available_models


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

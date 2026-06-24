"""Model reference resolution helpers for CLI commands."""

from __future__ import annotations

from pi_rpc.client.broker import request_broker


def model_ref(model: object) -> str | None:
    """Return provider/id for a model record when possible."""

    if not isinstance(model, dict):
        return None
    provider = model.get("provider")
    model_id = model.get("id")
    if isinstance(provider, str) and isinstance(model_id, str):
        return f"{provider}/{model_id}"
    if isinstance(model_id, str):
        return model_id
    return None


def extract_model_refs(data: object) -> list[str]:
    """Extract available model references from Pi response data."""

    if not isinstance(data, dict):
        return []
    models = data.get("models")
    if not isinstance(models, list):
        return []
    return [ref for model in models if (ref := model_ref(model)) is not None]


def resolve_model_from_available_models(
    requested_model: str,
    available_models: list[str] | None = None,
    *,
    available: list[str] | None = None,
) -> str:
    """Resolve a user model token to an available provider/model reference."""

    if available_models is None:
        available_models = available or []

    if requested_model in available_models:
        return requested_model

    suffix_matches = [model for model in available_models if model.endswith(f"/{requested_model}")]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    if len(suffix_matches) > 1:
        matches = ", ".join(sorted(suffix_matches))
        msg = f"Ambiguous model {requested_model!r}: {matches}"
        raise ValueError(msg)

    contains_matches = [model for model in available_models if requested_model in model]
    if len(contains_matches) == 1:
        return contains_matches[0]
    if len(contains_matches) > 1:
        matches = ", ".join(sorted(contains_matches))
        msg = f"Ambiguous model {requested_model!r}: {matches}"
        raise ValueError(msg)

    available_text = ", ".join(sorted(available_models)) or "none"
    msg = f"Unknown model {requested_model!r}. Available: {available_text}"
    raise ValueError(msg)


async def resolve_model_for_session(*, session_id: str, requested_model: str) -> str:
    """Resolve a requested model against live session models."""

    response = await request_broker(session_id, {"type": "models"})
    if response.get("type") != "response" or response.get("success") is not True:
        error = response.get("error", "could not fetch available models")
        raise RuntimeError(error)
    available = extract_model_refs(response.get("data"))
    return resolve_model_from_available_models(requested_model, available)

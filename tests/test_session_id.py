from __future__ import annotations

import pytest

from pi_rpc.session_id import (
    SessionIdError,
    session_file_stem,
    session_identity,
    validate_session_id,
)


@pytest.mark.parametrize("session_id", ["pi-rpc-dev", "review.main", "abc_123", "A-1"])
def test_validate_session_id_accepts_readable_handles(session_id: str) -> None:
    assert validate_session_id(session_id) == session_id


@pytest.mark.parametrize("session_id", ["", "has space", "slash/name", "emoji-🚀", ".", ".."])
def test_validate_session_id_rejects_unsafe_handles(session_id: str) -> None:
    with pytest.raises(SessionIdError):
        validate_session_id(session_id)


def test_session_file_stem_preserves_readable_prefix_and_adds_hash() -> None:
    stem = session_file_stem("pi-rpc-dev")

    assert stem.startswith("pi-rpc-dev-")
    assert len(stem.rsplit("-", 1)[-1]) == 12


def test_session_identity_contains_validated_value_and_file_stem() -> None:
    identity = session_identity("review-main")

    assert identity.value == "review-main"
    assert identity.file_stem.startswith("review-main-")

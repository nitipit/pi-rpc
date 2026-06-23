from __future__ import annotations

from pathlib import Path

import pytest

from pi_rpc.paths import paths_for_session


def test_paths_for_session_uses_safe_stem(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    state_dir = tmp_path / "state"
    monkeypatch.setattr("pi_rpc.paths.user_runtime_path", lambda *_, **__: runtime_dir)
    monkeypatch.setattr("pi_rpc.paths.user_state_path", lambda *_, **__: state_dir)

    paths = paths_for_session("pi-rpc-dev")

    assert paths.session_id == "pi-rpc-dev"
    assert paths.socket_path.parent == runtime_dir / "sessions"
    assert paths.pid_path.parent == runtime_dir / "sessions"
    assert paths.metadata_path.parent == state_dir / "sessions"
    assert paths.log_path.parent == state_dir / "sessions"
    assert paths.socket_path.name.startswith("pi-rpc-dev-")
    assert paths.socket_path.suffix == ".sock"

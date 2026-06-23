# pi-rpc

`pi-rpc` is the command-line remote control for long-running Pi RPC sessions.
It is designed to manage and communicate with `pi --mode rpc` processes through
explicit, readable `--session-id` handles.

## Current status

Implemented so far:

- a Python package managed by `uv`
- a Cyclopts-powered `pi-rpc` command
- readable `--session-id` validation
- platform-aware runtime/state paths through `platformdirs`
- a Unix-socket broker lifecycle
- a managed `pi --mode rpc --session-id <id>` subprocess behind the broker
- readiness handshake through Pi RPC `get_state`
- schema validation for broker control messages through `dictify`
- first tests and validation tooling (`ruff`, `ty`, `pytest`)

Prompt forwarding and event streaming are planned for later versions.

## First commands

```bash
uv run pi-rpc validate-session-id --session-id pi-rpc-dev
uv run pi-rpc paths --session-id pi-rpc-dev
uv run pi-rpc start --session-id pi-rpc-dev --name "Build pi-rpc"
uv run pi-rpc status --session-id pi-rpc-dev
uv run pi-rpc stop --session-id pi-rpc-dev
uv run pi-rpc sessions
```

`--session-id` is the stable, human-readable handle for one managed Pi RPC
session. Prefer shell-friendly ids such as `pi-rpc-dev`, `review-main`, or
`refactor.auth`.

## Development

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

See `goal/main.md` for the product goal and review perspectives.

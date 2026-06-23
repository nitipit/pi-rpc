# pi-rpc

`pi-rpc` is the command-line remote control for long-running Pi RPC sessions.
It is designed to manage and communicate with `pi --mode rpc` processes through
explicit, readable `--session-id` handles.

## v0.1 status

v0.1 is the project foundation. It provides:

- a Python package managed by `uv`
- a Cyclopts-powered `pi-rpc` command
- readable `--session-id` validation
- platform-aware runtime/state paths through `platformdirs`
- an initial modular transport boundary for future broker connections
- first tests and validation tooling (`ruff`, `ty`, `pytest`)

The broker and live Pi RPC subprocess management are planned for later versions.

## First commands

```bash
uv run pi-rpc validate-session-id --session-id pi-rpc-dev
uv run pi-rpc paths --session-id pi-rpc-dev
uv run pi-rpc status --session-id pi-rpc-dev
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

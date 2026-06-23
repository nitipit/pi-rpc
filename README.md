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
- prompt forwarding to the running Pi RPC process
- foreground event streaming until `agent_end`
- run-control pass-through for `steer`, `follow_up`, and `abort`
- model and thinking controls via `model`, `cycle-model`, `thinking`, `cycle-thinking`
- read-only visibility for `state`, `models`, `stats`, `messages`,
  `last-assistant-text`, and `commands`.
- human output from assistant text deltas and JSONL output for tools
- schema validation for broker control messages through `dictify`
- first tests and validation tooling (`ruff`, `ty`, `pytest`)

Steering/follow-up/abort are available via `steer`, `follow-up`, and `abort`.
Model/thinking controls are now available via `model`, `cycle-model`,
`thinking`, and `cycle-thinking`.
Read-only visibility remains via `state`, `models`, `stats`, `messages`,
`last-assistant-text`, and `commands`.
Richer extension UI handling is planned for later versions.

## First commands

```bash
uv run pi-rpc validate-session-id --session-id pi-rpc-dev
uv run pi-rpc paths --session-id pi-rpc-dev
uv run pi-rpc start --session-id pi-rpc-dev --name "Build pi-rpc"
uv run pi-rpc status --session-id pi-rpc-dev
uv run pi-rpc prompt --session-id pi-rpc-dev --message "Hello from pi-rpc"
uv run pi-rpc state --session-id pi-rpc-dev
uv run pi-rpc models --session-id pi-rpc-dev
uv run pi-rpc stats --session-id pi-rpc-dev
uv run pi-rpc messages --session-id pi-rpc-dev
uv run pi-rpc last-assistant-text --session-id pi-rpc-dev
uv run pi-rpc commands --session-id pi-rpc-dev
uv run pi-rpc model --session-id pi-rpc-dev gpt-4
uv run pi-rpc cycle-model --session-id pi-rpc-dev
uv run pi-rpc thinking --session-id pi-rpc-dev high
uv run pi-rpc cycle-thinking --session-id pi-rpc-dev
uv run pi-rpc steer --session-id pi-rpc-dev --message "Adjust the implementation"
uv run pi-rpc follow-up --session-id pi-rpc-dev --message "Then run tests"
uv run pi-rpc abort --session-id pi-rpc-dev
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

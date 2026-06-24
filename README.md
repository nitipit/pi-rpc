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
- session behavior controls via `name`, `compact`, queue modes, retry, and auto-compaction
- read-only visibility for `state`, `models`, `stats`, `messages`,
  `last-assistant-text`, and `commands`.
- human output from assistant text deltas and JSONL output for tools
- shell command controls via `bash` and `abort-bash`
- extension UI response bridge via `ui-respond`
- schema validation for broker control messages through `dictify`
- first tests and validation tooling (`ruff`, `ty`, `pytest`)
- Docusaurus docs foundation (`docs-site/`) for command and extension UI docs

Steering/follow-up/abort are available via `steer`, `follow-up`, and `abort`.
Model/thinking controls are now available via `model`, `cycle-model`,
`thinking`, and `cycle-thinking`.
Read-only visibility remains via `state`, `models`, `stats`, `messages`,
`last-assistant-text`, and `commands`.
Session behavior controls are available via `name`, `compact`, `auto-compaction`,
`auto-retry`, `steering-mode`, `follow-up-mode`, and `abort-retry`.
Shell controls are available via `bash` and `abort-bash`.
Extension UI requests from prompt streams can be answered with `ui-respond`.
Branch/session controls are available via `new-session`, `switch-session`, `clone`,
`fork`, `fork-messages`, and `export-html`.
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
uv run pi-rpc name --session-id pi-rpc-dev "Build pi-rpc"
uv run pi-rpc compact --session-id pi-rpc-dev --instructions "Focus on implementation decisions"
uv run pi-rpc auto-compaction --session-id pi-rpc-dev on
uv run pi-rpc auto-retry --session-id pi-rpc-dev on
uv run pi-rpc steering-mode --session-id pi-rpc-dev one-at-a-time
uv run pi-rpc follow-up-mode --session-id pi-rpc-dev all
uv run pi-rpc abort-retry --session-id pi-rpc-dev
uv run pi-rpc new-session --session-id pi-rpc-dev --parent-session /tmp/parent-session
uv run pi-rpc switch-session --session-id pi-rpc-dev /tmp/branch-session
uv run pi-rpc clone --session-id pi-rpc-dev
uv run pi-rpc fork --session-id pi-rpc-dev entry-1
uv run pi-rpc fork-messages --session-id pi-rpc-dev
uv run pi-rpc export-html --session-id pi-rpc-dev
uv run pi-rpc export-html --session-id pi-rpc-dev --output-path /tmp/session-export.html
uv run pi-rpc bash --session-id pi-rpc-dev "git status"
uv run pi-rpc abort-bash --session-id pi-rpc-dev
uv run pi-rpc ui-respond --session-id pi-rpc-dev ui-request-id --value "Allow"
uv run pi-rpc ui-respond --session-id pi-rpc-dev ui-request-id --confirmed true
uv run pi-rpc ui-respond --session-id pi-rpc-dev ui-request-id --cancelled
uv run pi-rpc steer --session-id pi-rpc-dev --message "Adjust the implementation"
uv run pi-rpc follow-up --session-id pi-rpc-dev --message "Then run tests"
uv run pi-rpc abort --session-id pi-rpc-dev
uv run pi-rpc stop --session-id pi-rpc-dev
uv run pi-rpc sessions
```

`--session-id` is the stable, human-readable handle for one managed Pi RPC
session. Prefer shell-friendly ids such as `pi-rpc-dev`, `review-main`, or
`refactor.auth`.

## Documentation

```bash
deno task docs:dev

deno task docs:build
```

## Development

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

See `goal/main.md` for the product goal and review perspectives.

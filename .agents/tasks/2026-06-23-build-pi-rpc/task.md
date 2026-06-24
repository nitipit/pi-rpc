---
id: 2026-06-23-build-pi-rpc
title: Build pi-rpc
status: doing
created: 2026-06-23T23:00:10+07:00
updated: 2026-06-24T08:35:41+07:00
blocked_by: []
---

## Goal

Build `pi-rpc` into the command-line remote control for long-running Pi RPC
sessions described in `goal/main.md`.

## Scope

Work version by version, starting with v0.1. Keep each version meaningful,
validated, and committed before moving on.

## Checklist

- [x] v0.1 foundation: Python/uv/cyclopts scaffold, session-id basics, path
      helpers, first tests, and project workflow files.
- [x] v0.2 broker lifecycle: start/status/stop a local Unix-socket broker,
      persist metadata, validate broker control messages with Dictify.
- [x] v0.3 Pi subprocess: broker starts a real `pi --mode rpc --session-id`
      child, handshakes with `get_state`, reports Pi readiness/status.
- [x] v0.4 prompt streaming: forward prompt payloads to Pi RPC, stream native
      events until `agent_end`, print text deltas for humans and JSONL for tools.
- [x] v0.5 run-control: steer/follow-up/abort pass-through.
- [x] v0.6 read-only session visibility: `state`, `models`, `stats`.
- [x] v0.7 broader read-only inspection: `messages`, `last-assistant-text`,
      `commands`.
- [x] v0.8 model/thinking controls: `model`, `cycle-model`, `thinking`,
      `cycle-thinking`.
- [x] v0.9 session behavior controls: `name`, `compact`, auto controls,
      queue modes, and `abort-retry`.
- [x] v0.10 session file/branch controls: new-session, switch-session, clone, fork, fork-messages, export-html.
- [x] v0.11 shell command controls: `bash` and `abort-bash`.
- [x] v0.12 extension UI response bridge: `ui-respond`.
- [x] v0.13 Docusaurus docs foundation with Deno tasks and baseline pages (`intro`, `commands`, `extension-ui`).
- [x] v0.14 CI and packaging validation workflow.
- [x] v0.15 interactive extension UI handling for human prompt streams.
- [x] v0.16 RPC payload controls for prompt streaming behavior and bash context exclusion.
- [ ] Later versions: image attachments and docs polish.

## Attachments

None

## Blockers

None

## Notes

Use `--session-id` as the explicit readable stable identity. Keep transport
modular so Unix socket can later grow into TCP or other transports.

## Activity

- 2026-06-23T23:00:10+07:00 — Created task card and started v0.1 foundation.
- 2026-06-23T23:13:35+07:00 — Implemented and validated v0.1 foundation.
- 2026-06-23T23:35:32+07:00 — Implemented v0.2 broker lifecycle skeleton and Dictify schema validation.
- 2026-06-23T23:49:10+07:00 — Implemented v0.3 real Pi RPC subprocess startup and readiness handshake.
- 2026-06-24T00:00:53+07:00 — Delegated v0.4 implementation to python-runtime-engineer and added prompt/event streaming.
- 2026-06-24T00:06:25+07:00 — Delegated and implemented v0.5 run-control pass-through and CLI surface commands.
- 2026-06-24T00:16:03+07:00 — Delegated and implemented v0.6 read-only session visibility commands.
- 2026-06-24T00:22:59+07:00 — Delegated and implemented v0.7 broader read-only inspection commands.
- 2026-06-24T00:48:11+07:00 — Implemented v0.8 model/thinking controls.
- 2026-06-24T01:05:12+07:00 — Implemented v0.9 session behavior controls.
- 2026-06-24T06:49:50+07:00 — Implemented v0.10 session file/branch controls and broker mappings.
- 2026-06-24T07:16:26+07:00 — Implemented v0.11 shell command controls (`bash`/`abort-bash`) and validation updates.
- 2026-06-24T07:46:50+07:00 — Implemented v0.12 extension UI response bridge.
- 2026-06-24T08:05:05+07:00 — Implemented v0.13 Docusaurus docs foundation.
- 2026-06-24T08:07:31+07:00 — Implemented v0.14 CI and packaging validation workflow.
- 2026-06-24T08:17:39+07:00 — Implemented v0.15 interactive extension UI handling for human prompt streams.
- 2026-06-24T08:35:41+07:00 — Implemented v0.16 RPC payload controls for prompt streaming behavior and bash context exclusion.

# Pi RPC Protocol Role

## Duty
Review `pi-rpc` against Pi's native RPC mode, session behavior, events, and
extension UI protocol.

## Use When
- Mapping Pi RPC commands/events to `pi-rpc` commands.
- Checking session options and runtime session behavior.
- Reviewing protocol framing, response correlation, event streaming, or
  extension UI handling.

## Do Not Use When
- The task is only product wording or docs polish.
- The work does not touch Pi RPC compatibility.

## Role Package
- Behavior contract: `AGENTS.md`
- Invocation/runtime config: `session.md`
- Role cues: `.agents/roles/pi-rpc-protocol/cues.md`
- Task workspace: `tasks/`

## Cue Path
```text
.agents/roles/pi-rpc-protocol/cues.md
```

## Boundary Notes
- Treat Pi docs/manual as authoritative.
- Prefer fresh inspection over stale memory for protocol-sensitive review.

# Python Runtime Engineer Role

## Duty
Implement the Python `pi-rpc` runtime: uv project setup, Cyclopts CLI,
platformdirs paths, subprocess/broker logic, transports, structured output, and
tests.

## Use When
- Writing or refactoring Python implementation.
- Designing broker, transport, process, or client modules.
- Adding Python dependencies or validation tooling.
- Fixing tests, lint, or type-check issues.

## Do Not Use When
- The task is only product naming or protocol coverage review.
- Fresh independent quality review is needed after implementation.

## Role Package
- Behavior contract: `AGENTS.md`
- Invocation/runtime config: `session.md`
- Role cues: `.agents/roles/python-runtime-engineer/cues.md`
- Task workspace: `tasks/`

## Cue Path
```text
.agents/roles/python-runtime-engineer/cues.md
```

## Boundary Notes
- Keep modules cleanly separated so future TCP or other transports are possible.
- Follow uv, cyclopts, platformdirs, ruff, ty, and pytest conventions.

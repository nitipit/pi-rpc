# Docs Packaging Role

## Duty
Keep `pi-rpc` documentation, packaging notes, install guidance, and examples
usable as the product evolves.

## Use When
- Creating or updating Docusaurus docs.
- Writing README/install/usage examples.
- Reviewing packaging metadata or user onboarding.

## Do Not Use When
- Runtime implementation or protocol correctness is the main risk.

## Role Package
- Behavior contract: `AGENTS.md`
- Invocation/runtime config: `session.md`
- Role cues: `.agents/roles/docs-packaging/cues.md`
- Task workspace: `tasks/`

## Cue Path
```text
.agents/roles/docs-packaging/cues.md
```

## Boundary Notes
- Use Docusaurus and Deno-stack guidance from root `AGENTS.md`.
- Document only real or clearly marked future-capable behavior.

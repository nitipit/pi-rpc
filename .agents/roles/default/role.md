# Default Role

## Duty
Coordinate `pi-rpc` development across sessions. Keep the product goal, cues,
version flow, roles, implementation, validation, docs, and commits aligned.

## Use When
- Starting or restoring work in this repo.
- Planning product, architecture, implementation, validation, or docs work.
- Deciding whether specialist repo-local roles should be created or used.
- Coordinating versioned development and meaningful git commits.
- Reviewing whether work still serves the `pi-rpc` product goal.

## Do Not Use When
- A narrow specialist role has already been selected for a bounded task.
- The user explicitly asks the current session to act as another role.
- A fresh independent review is more useful than continuity.

## Role Package
- Behavior contract: `AGENTS.md`
- Invocation/runtime config: `session.md`
- Role cues: `.agents/roles/default/cues.md`
- Task workspace: `tasks/`

## Cue Path
```text
.agents/roles/default/cues.md
```

## Boundary Notes
- This role coordinates; it does not replace specialist review when fresh
  protocol, product, implementation, docs, or quality perspectives are useful.
- Keep durable product direction in `goal/main.md`, not in task cards or cues.
- Keep implementation status and plans in task management, not in goal files.

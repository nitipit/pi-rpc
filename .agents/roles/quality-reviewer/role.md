# Quality Reviewer Role

## Duty
Provide fresh validation and review for completed `pi-rpc` product versions or
implementation chunks.

## Use When
- A version or feature claims to be complete.
- Tests, lint, type checks, manual CLI behavior, or docs need independent review.
- Checking for hidden current-session assumptions, broken `--session-id` behavior,
  or mismatch with `goal/main.md`.

## Do Not Use When
- The work is still exploratory or obviously incomplete.
- The task needs ongoing implementation context more than fresh review.

## Role Package
- Behavior contract: `AGENTS.md`
- Invocation/runtime config: `session.md`
- Role cues: `.agents/roles/quality-reviewer/cues.md`
- Task workspace: `tasks/`

## Cue Path
```text
.agents/roles/quality-reviewer/cues.md
```

## Boundary Notes
- Review with a fresh perspective.
- Report must-fix findings separately from optional polish.

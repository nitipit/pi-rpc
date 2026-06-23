# Release Decider Role

## Duty
Act as the final cross-agent gate after `pi-rpc` is working as a product. Decide
whether active development should stop, continue with another focused version,
or replan against the product goal.

## Use When
- `pi-rpc` is working end-to-end enough that the default agent thinks the product
  may be finishable.
- Core lifecycle, prompt/control, session visibility, validation, and docs have
  been implemented enough to judge product sufficiency.
- The project needs a final cross-agent stop/continue/replan decision.
- Remaining work may be only enhancement, polish, or optional backlog.

## Do Not Use When
- The product is still in normal implementation versions.
- Core lifecycle/prompt/session behavior is not implemented yet.
- A normal version still has a clear next core implementation step.
- The task is only routine implementation, docs, git, or protocol mapping.
- The user has explicitly defined the next version and no final stop decision is
  needed.

## Role Package
- Behavior contract: `AGENTS.md`
- Invocation/runtime config: `session.md`
- Role cues: `.agents/roles/release-decider/cues.md`
- Task workspace: `tasks/`

## Cue Path
```text
.agents/roles/release-decider/cues.md
```

## Boundary Notes
- Make a decision instead of asking the user by default.
- Ask only if the goal itself conflicts, a required external decision is missing,
  or validation cannot be performed because of an external blocker.
- Prefer stopping when remaining work is mostly enhancement rather than core goal
  completion.

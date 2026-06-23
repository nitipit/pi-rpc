# Default Role Behavior

You are the default coordinator for `pi-rpc`.

## Required Context

Before substantial work, read or refresh:

- `goal/main.md` for product direction and review perspectives.
- `.agents/roles/default/cues.md` for compact cross-session anchors.
- `AGENTS.md` for repo-wide workflow instructions.

## How To Work

- Keep `pi-rpc` aligned with the product goal: a command-line remote control for
  long-running Pi RPC sessions.
- Treat `--session-id` as the explicit, readable, stable identity for a managed
  Pi RPC session.
- Develop in flexible product versions: `v0.1`, `v0.2`, ..., with meaningful
  validated git commits.
- Prefer discussion before changing product behavior, architecture, workflow,
  role structure, or public command names.
- Use repo-local roles when they materially improve product judgment,
  implementation quality, protocol coverage, documentation, or validation.
- Do not use `release-decider` during normal implementation versions. Hold it
  until `pi-rpc` is working as a product and the project needs a final
  cross-agent stop/continue/replan decision against `goal/main.md`. Continue
  development until the user says to pause or the final release-decider gate
  says to pause/stop.
- For stateful role sessions, reuse valid context. Do not repeatedly resend the
  full initial prompt or unchanged role context; send only new facts, changed
  facts, task constraints, and expected output. If context validity is unclear,
  do a small context check or refresh only the missing instructions.
- Keep implementation modular, especially around broker transport, so future TCP
  or other transports can be added without rewriting the product.
- Update cues after durable decisions or workflow changes that future sessions
  should recover quickly.

## Documentation

- Use Docusaurus for docs.
- Use the Deno stack for JavaScript and TypeScript tooling.
- Improve docs incrementally as product features become real.

## Boundaries

- Do not store implementation plans or task status in `goal/main.md`.
- Do not commit broken or partial implementation unless the user explicitly asks
  for a checkpoint commit.
- Do not create hidden current-session behavior that undermines explicit
  `--session-id` usage.

# Agent Instructions

Act as the repo-local default role unless the user explicitly selects another
role. Use `.agents/roles/default/role.md` for routing context and
`.agents/roles/default/AGENTS.md` for the default role behavior contract.

Before making product, architecture, or implementation decisions for this repo,
read `goal/main.md` and use it as the alignment source for `pi-rpc`.

When restoring context, starting a new session, or planning substantial work,
skim `.agents/roles/default/cues.md` for compact context anchors from previous
sessions.

Keep goal files focused on durable product direction. Put implementation plans,
status, and task details somewhere else.

## Development Workflow

Develop `pi-rpc` one meaningful product version at a time: `v0.1`, `v0.2`,
..., `v0.10`, `v0.11`, and so on until the product goal is reached.

For each version, define the product step, implement it, validate it, then
create a git commit for meaningful completed work. Each version should move the
product measurably closer to `goal/main.md`, not just add technical pieces.
After each version, choose the next meaningful product version from the
remaining goal gaps before continuing. Do not commit broken or partial
implementation unless explicitly asked for a checkpoint commit.

Version scope may be adjusted as the product becomes clearer. Repo-local roles
may also be created, revised, or removed when doing so improves product quality,
implementation flow, or review quality.

## Delegation Workflow

Delegate to repo-local roles when the task clearly matches a role's duty. Try
delegation first by default, unless doing the work directly has a clear benefit
for speed, context continuity, simplicity, or avoiding unnecessary coordination
overhead. Delegation is also for context hygiene: keep implementation details,
git details, protocol concerns, docs work, and review findings in the matching
role context instead of polluting the default coordinator role.

Keep delegated tasks bounded and token-efficient. Prefer specialist roles for
product judgment, protocol review, implementation-heavy work, fresh quality
review, docs/packaging, and other clearly scoped responsibilities.

Do not use the `release-decider` role during normal implementation versions.
Hold it until `pi-rpc` is working as a product and the project needs a final
cross-agent stop/continue/replan decision. At that point, use release-decider to
judge whether active development should stop, pause, or continue further against
`goal/main.md` without asking the user by default. Continue development until
the user says to pause or the final release-decider gate says to pause/stop.

For temporary/stateless Pi role work, use `pi --no-session` and close any tmux
or terminal-multiplexer session after capturing the result. Do not use
`--session-id` for disposable review/delegation work unless durable Pi session
state is explicitly intended.

For stateful role sessions, do not repeatedly resend the full initial role
prompt or unchanged context. Reuse the session's valid context and send only new
facts, changed facts, task constraints, and expected output. If unsure whether a
stateful session still has its initial context, first send a small context check
or refresh the missing role instructions only.

## Role Model Policy

Use GPT models for repo-local role sessions with provider-qualified Pi model
IDs. Prefer token-efficient delegation: use
`openai-codex/gpt-5.3-codex-spark` for implementation-heavy and docs tasks,
`openai-codex/gpt-5.4` for coordinator/product/protocol judgment, and reserve
`openai-codex/gpt-5.5` for bounded fresh quality-review and release-decision
passes where the higher quality is worth the cost.

## Documentation Workflow

Use Docusaurus for project documentation and improve the docs incrementally as
the product evolves. Keep docs user-facing first, with architecture and
reference material added as features become real.

Use the Deno stack for JavaScript and TypeScript tooling in this repo. When a
Docusaurus workflow depends on Node/npm ecosystem packages, prefer Deno-managed
configuration and tasks where practical, and keep any unavoidable Node-specific
usage isolated and explicit.

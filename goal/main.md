# Product Goal

`pi-rpc` is the command-line remote control for long-running Pi sessions. It
lets a user keep a Pi session alive by explicit `--session-id`, send prompts to
that session from any terminal or tool, observe progress, and control the
session without reopening Pi's full interactive interface.

The product should feel like a native companion to Pi rather than a replacement
for Pi. It should preserve Pi's session concepts and naming, expose Pi RPC
capabilities in clear product features, and stay useful for both humans at a
terminal and tools that need structured, dependable control of a running
session.

## Product Features

- Keep a Pi session alive and address it explicitly by `--session-id`.
- Prompt a running session from anywhere.
- Continue the same work across terminals, scripts, editors, and automation.
- See whether a session is running, idle, busy, or waiting for input.
- Watch live assistant progress, tool activity, retries, compaction, and
  completion.
- Steer, follow up, or abort a session while work is in progress.
- Inspect, rename, switch, clone, fork, export, and review Pi sessions.
- Change model and thinking settings for a running session.
- Offer human-readable output and structured output for tools.
- Let Pi extensions request confirmation, choices, input, or editor text even
  when Pi is running headlessly.

## Review Perspectives

Meaningful product or implementation changes should be reviewed against these
stable perspectives:

- Session explicitness: every action should make the target Pi session clear.
- Native Pi compatibility: names and behavior should follow Pi where practical.
- Human control: terminal users should understand what is happening and retain
  control during long-running work.
- Automation friendliness: scripts and tools should receive predictable commands,
  outputs, and errors.
- Full RPC coverage: features exposed by Pi RPC should have a clear path into
  `pi-rpc` without inventing a separate product model.

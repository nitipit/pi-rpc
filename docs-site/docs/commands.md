---
title: Commands
description: Reference for pi-rpc command categories
sidebar_position: 2
---

# Commands

`pi-rpc` exposes command groups for control, visibility, session management,
stateless runs, and detached jobs.

## Session lifecycle

- `start`, `status`, `stop`, `sessions`
- `new-session`, `switch-session`, `clone`, `fork`, `fork-messages`, `export-html`

## Prompting and run control

- `prompt` streams assistant text, can attach images with repeated `--image`,
  can queue with `--streaming-behavior`, can run in the background with
  `--detach`, and can answer dialog extension UI requests interactively in
  human terminal output
- `run` starts a disposable stateless `pi --mode rpc --no-session` task; it can
  attach images, select model/thinking, and run in the background with `--detach`
- `steer`, `follow-up`, `abort`; `steer` and `follow-up` can also attach images
  with repeated `--image`

## Visibility

- `state`, `models`, `stats`, `messages`, `last-assistant-text`, `commands`

## Detached jobs

- `jobs` lists detached stateless and stateful prompt jobs
- `job-status <job-id>` shows metadata, paths, status, and errors
- `job-result <job-id>` prints captured assistant text or JSON frames

## Model and behavior controls

- `model`, `cycle-model`
- `thinking`, `cycle-thinking`
- `name`, `compact`, `auto-compaction`, `auto-retry`, `steering-mode`,
  `follow-up-mode`, `abort-retry`

## Shell and extension UI

- `bash`, `abort-bash`; use `bash --exclude-from-context` for inspection output
  that should not be injected into the next prompt
- `ui-respond`

Stateful session commands support `--session-id`, which is the key contract for
explicitness. The `run` command is intentionally stateless and does not require
`--session-id`.

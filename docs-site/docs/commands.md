---
title: Commands
description: Reference for pi-rpc command categories
sidebar_position: 2
---

# Commands

`pi-rpc` exposes command groups for control, visibility, and session management.

## Session lifecycle

- `start`, `status`, `stop`, `sessions`
- `new-session`, `switch-session`, `clone`, `fork`, `fork-messages`, `export-html`

## Prompting and run control

- `prompt` streams assistant text and can answer dialog extension UI requests
  interactively in human terminal output
- `steer`, `follow-up`, `abort`

## Visibility

- `state`, `models`, `stats`, `messages`, `last-assistant-text`, `commands`

## Model and behavior controls

- `model`, `cycle-model`
- `thinking`, `cycle-thinking`
- `name`, `compact`, `auto-compaction`, `auto-retry`, `steering-mode`,
  `follow-up-mode`, `abort-retry`

## Shell and extension UI

- `bash`, `abort-bash`
- `ui-respond`

Each command supports `--session-id`, which is the key contract for explicitness.

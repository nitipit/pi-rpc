---
title: Intro
description: Overview of pi-rpc command-line workflow
slug: /
sidebar_position: 1
---

# Intro

`pi-rpc` is the command-line companion for controlling a long-running Pi session
through Pi RPC. It uses an explicit `--session-id` to address exactly one session
at a time.

## Why this project exists

Pi sessions can run for long periods while you move between terminals.
`pi-rpc` lets you continue and steer that work without reopening the full Pi
interactive UI.

## Core workflow

1. Create or identify a session id, for example `pi-rpc-dev`.
2. Start or reuse a session with that id.
3. Send prompt, control, visibility, and maintenance commands from anywhere.
4. Keep using the same id until the work is done.

## Design anchor

All commands are explicit about which session they target; `--session-id` remains
human-readable and stable across terminals.

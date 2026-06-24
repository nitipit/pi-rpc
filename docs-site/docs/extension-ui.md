---
title: Extension UI
description: Handling extension requests and interactive responses
sidebar_position: 3
---

# Extension UI

Some Pi extensions can pause work and request user input while the session continues.
In human `prompt` output, `pi-rpc` can answer dialog requests interactively when
stdin is a terminal. JSON output remains raw JSONL and never prompts.

## Prompt-mode interaction

`prompt` handles common dialog methods directly:

- `select`: choose by number or exact value
- `confirm`: answer yes/no, or cancel
- `input`: enter one line of text, including an empty string
- `editor`: enter multiple lines and submit with `.end`

Use `/cancel` for single-line dialogs or `.cancel` for editor dialogs. For
`select`, pressing Enter without a choice also cancels.

## Manual responses

`ui-respond` remains available for scripts, non-interactive prompt streams, and
operators who want to answer a request from a separate shell:

- `ui-respond --value <text>`
- `ui-respond --confirmed <true|false>`
- `ui-respond --cancelled`

## Typical pattern

1. Extension requests input and Pi emits UI metadata in the prompt stream.
2. If the stream is interactive, answer the prompt directly.
3. Otherwise, copy the request id and respond with the matching `ui-respond`
   option.

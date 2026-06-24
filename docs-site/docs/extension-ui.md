---
title: Extension UI
description: Handling extension requests and interactive responses
sidebar_position: 3
---

# Extension UI

Some Pi extensions can pause work and request user input while the session continues.
`pi-rpc` exposes `ui-respond` so operators can answer those requests from the
terminal.

## Current support

- `ui-respond --value <text>`
- `ui-respond --confirmed <true|false>`
- `ui-respond --cancelled`

## Typical pattern

1. Extension requests input and Pi emits UI metadata in event stream.
2. Operator inspects the request context.
3. Respond with the matching `ui-respond` option and continue.

For now this is focused on operational handling; richer interactive UI tooling can
be added in later versions.

# Pi RPC Protocol Behavior

You review `pi-rpc` for compatibility with Pi RPC mode.

Before protocol-sensitive work, inspect the relevant Pi documentation, especially
`docs/rpc.md`, and use the actual protocol as the source of truth.

Focus on:

- JSONL stdin/stdout framing
- command/response correlation by `id`
- event streaming and fanout semantics
- session commands and `--session-id` startup behavior
- extension UI request/response handling
- native Pi naming and behavior

Do not invent a separate protocol model unless explicitly asked.

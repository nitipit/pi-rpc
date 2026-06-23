# Docs Packaging Session

```yaml
cli: pi
role: docs-packaging
model: openai-codex/gpt-5.3-codex-spark
reasoning: medium
session: stateless
cwd: /home/nitipit/space/code/umlab/pi-role-session
tools:
  - read
  - bash
  - edit
  - write
  - grep/find
output:
  final_only: unsupported
  mode: cli-default
transport:
  kind: terminal-multiplexer
  manager: tmux
  session_name: pi-rpc-docs-packaging
  close: after-task
  capture: bounded-tail
```

Use bounded docs tasks and avoid loading unrelated implementation context.

## Commands

### Start
```bash
tmux new-session -Ad -s pi-rpc-docs-packaging -c /home/nitipit/space/code/umlab/pi-role-session 'pi --session-id pi-rpc-docs-packaging --model openai-codex/gpt-5.3-codex-spark --thinking medium'
```

### Run Task
```bash
tmux send-keys -t pi-rpc-docs-packaging '<bounded docs/packaging task>' Enter
```

### Capture Result
```bash
tmux capture-pane -pt pi-rpc-docs-packaging -S -120
```

### Interrupt
```bash
tmux send-keys -t pi-rpc-docs-packaging C-c
```

### Close
```bash
tmux kill-session -t pi-rpc-docs-packaging
```

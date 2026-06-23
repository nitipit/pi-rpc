# Quality Reviewer Session

```yaml
cli: pi
role: quality-reviewer
model: openai-codex/gpt-5.5
reasoning: high
session: stateless
cwd: /home/nitipit/space/code/umlab/pi-role-session
tools:
  - read
  - bash
  - grep/find
output:
  final_only: unsupported
  mode: cli-default
transport:
  kind: terminal-multiplexer
  manager: tmux
  session_name: pi-rpc-quality-reviewer
  close: after-task
  capture: bounded-tail
```

Use bounded, fresh review tasks. Prefer targeted inspection and validation over
large context loading.

## Commands

### Start
```bash
tmux new-session -Ad -s pi-rpc-quality-reviewer -c /home/nitipit/space/code/umlab/pi-role-session 'pi --session-id pi-rpc-quality-reviewer --model openai-codex/gpt-5.5 --thinking high'
```

### Run Task
```bash
tmux send-keys -t pi-rpc-quality-reviewer '<bounded quality review task>' Enter
```

### Capture Result
```bash
tmux capture-pane -pt pi-rpc-quality-reviewer -S -120
```

### Interrupt
```bash
tmux send-keys -t pi-rpc-quality-reviewer C-c
```

### Close
```bash
tmux kill-session -t pi-rpc-quality-reviewer
```

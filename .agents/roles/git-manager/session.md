# Git Manager Session

```yaml
cli: pi
role: git-manager
model: openai-codex/gpt-5.3-codex-spark
reasoning: low
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
  session_name: pi-rpc-git-manager
  close: after-task
  capture: bounded-tail
```

Use bounded tasks. Inspect status before any staging or commit. Do not run
destructive git operations without explicit user confirmation.

## Commands

### Start
```bash
tmux new-session -Ad -s pi-rpc-git-manager -c /home/nitipit/space/code/umlab/pi-role-session 'pi --session-id pi-rpc-git-manager --model openai-codex/gpt-5.3-codex-spark --thinking low'
```

### Run Task
```bash
tmux send-keys -t pi-rpc-git-manager '<bounded git management task>' Enter
```

### Capture Result
```bash
tmux capture-pane -pt pi-rpc-git-manager -S -120
```

### Interrupt
```bash
tmux send-keys -t pi-rpc-git-manager C-c
```

### Close
```bash
tmux kill-session -t pi-rpc-git-manager
```

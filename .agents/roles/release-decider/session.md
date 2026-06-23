# Release Decider Session

```yaml
cli: pi
role: release-decider
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
  session_name: pi-rpc-release-decider
  close: after-task
  capture: bounded-tail
```

Use bounded, fresh stop/continue reviews. Load only the goal, current task card,
relevant docs, and validation evidence needed to decide.

## Commands

### Start
```bash
tmux new-session -Ad -s pi-rpc-release-decider -c /home/nitipit/space/code/umlab/pi-role-session 'pi --session-id pi-rpc-release-decider --model openai-codex/gpt-5.5 --thinking high'
```

### Run Task
```bash
tmux send-keys -t pi-rpc-release-decider '<bounded release decision task>' Enter
```

### Capture Result
```bash
tmux capture-pane -pt pi-rpc-release-decider -S -120
```

### Interrupt
```bash
tmux send-keys -t pi-rpc-release-decider C-c
```

### Close
```bash
tmux kill-session -t pi-rpc-release-decider
```

# Python Runtime Engineer Session

```yaml
cli: pi
role: python-runtime-engineer
model: gpt-5.3-codex-spark
reasoning: high
session: stateful
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
  session_name: pi-rpc-python-runtime-engineer
  close: explicit-only
  capture: bounded-tail
```

## Commands

### Start
```bash
tmux new-session -Ad -s pi-rpc-python-runtime-engineer -c /home/nitipit/space/code/umlab/pi-role-session 'pi --session-id pi-rpc-python-runtime-engineer --model gpt-5.3-codex-spark --thinking high'
```

### Run Task
```bash
tmux send-keys -t pi-rpc-python-runtime-engineer '<bounded Python runtime implementation task>' Enter
```

### Capture Result
```bash
tmux capture-pane -pt pi-rpc-python-runtime-engineer -S -120
```

### Interrupt
```bash
tmux send-keys -t pi-rpc-python-runtime-engineer C-c
```

### Close
```bash
tmux kill-session -t pi-rpc-python-runtime-engineer
```

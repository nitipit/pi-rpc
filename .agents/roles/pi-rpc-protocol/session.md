# Pi RPC Protocol Session

```yaml
cli: pi
role: pi-rpc-protocol
model: gpt-5.4
reasoning: high
session: stateless
cwd: /home/nitipit/space/code/umlab/pi-role-session
tools:
  - read
  - grep/find
  - bash
output:
  final_only: unsupported
  mode: cli-default
transport:
  kind: terminal-multiplexer
  manager: tmux
  session_name: pi-rpc-protocol-reviewer
  close: after-task
  capture: bounded-tail
```

## Commands

### Start
```bash
tmux new-session -Ad -s pi-rpc-protocol-reviewer -c /home/nitipit/space/code/umlab/pi-role-session 'pi --session-id pi-rpc-protocol-reviewer --model gpt-5.4 --thinking high'
```

### Run Task
```bash
tmux send-keys -t pi-rpc-protocol-reviewer '<bounded Pi RPC protocol review task>' Enter
```

### Capture Result
```bash
tmux capture-pane -pt pi-rpc-protocol-reviewer -S -120
```

### Interrupt
```bash
tmux send-keys -t pi-rpc-protocol-reviewer C-c
```

### Close
```bash
tmux kill-session -t pi-rpc-protocol-reviewer
```

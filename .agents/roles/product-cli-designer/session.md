# Product CLI Designer Session

```yaml
cli: pi
role: product-cli-designer
model: gpt-5.4
reasoning: medium
session: stateless
cwd: /home/nitipit/space/code/umlab/pi-role-session
tools:
  - read
  - grep/find
output:
  final_only: unsupported
  mode: cli-default
transport:
  kind: terminal-multiplexer
  manager: tmux
  session_name: pi-rpc-product-cli-designer
  close: after-task
  capture: bounded-tail
```

## Commands

### Start
```bash
tmux new-session -Ad -s pi-rpc-product-cli-designer -c /home/nitipit/space/code/umlab/pi-role-session 'pi --session-id pi-rpc-product-cli-designer --model gpt-5.4 --thinking medium --no-tools'
```

### Run Task
```bash
tmux send-keys -t pi-rpc-product-cli-designer '<bounded product CLI review task>' Enter
```

### Capture Result
```bash
tmux capture-pane -pt pi-rpc-product-cli-designer -S -120
```

### Interrupt
```bash
tmux send-keys -t pi-rpc-product-cli-designer C-c
```

### Close
```bash
tmux kill-session -t pi-rpc-product-cli-designer
```

# Default Role Session

```yaml
cli: pi
role: default
model: gpt-5.4
reasoning: medium
session: stateful
cwd: /home/nitipit/space/code/umlab/pi-role-session
tools:
  - read
  - bash
  - edit
  - write
  - grep/find
  - web/code search when needed
output:
  final_only: unsupported
  mode: cli-default
transport:
  kind: terminal-multiplexer
  manager: tmux
  session_name: pi-rpc-default-role
  close: explicit-only
  capture: bounded-tail
```

Use this role as the stateful coordinator for ongoing `pi-rpc` development.
Start or reuse the managed terminal session when explicit role invocation is
needed. The current interactive assistant may also act as this role when the
repo root `AGENTS.md` selects it.

## Commands

### Start
```bash
tmux new-session -Ad -s pi-rpc-default-role -c /home/nitipit/space/code/umlab/pi-role-session 'pi --session-id pi-rpc-default-role --model gpt-5.4 --thinking medium'
```

### Run Task
```bash
tmux send-keys -t pi-rpc-default-role '<bounded task for the default coordinator>' Enter
```

### Capture Result
```bash
tmux capture-pane -pt pi-rpc-default-role -S -120
```

### Interrupt
```bash
tmux send-keys -t pi-rpc-default-role C-c
```

### Close
```bash
tmux kill-session -t pi-rpc-default-role
```

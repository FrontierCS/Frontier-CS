# Generals.io Bot Images

Build the task-specific Harbor images before running a local Harbor trial:

```bash
bash 2.0/problems/generals_io_bot/docker/build_images.sh
```

The images install `strakam/generals-bots` from pinned commit
`c2b77bf72812ec91fb2024d80d90112b961dfa7e` plus explicit CPU `jax/jaxlib`
dependencies used by the simulator.

- Agent image: exposes `/app/generals_agent` as a git checkout for the agent.
- Judge image: keeps a clean copy at `/opt/generals-agent-clean` for patch application.

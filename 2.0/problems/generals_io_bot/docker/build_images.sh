#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
TASK_DIR="$ROOT/2.0/problems/generals_io_bot"
COMMIT="${GENERALS_BOTS_COMMIT:-c2b77bf72812ec91fb2024d80d90112b961dfa7e}"
SHORT="${COMMIT:0:7}"
AGENT_TAG="${AGENT_TAG:-frontiercs/generals-io-bot-agent:experimental-${SHORT}}"
JUDGE_TAG="${JUDGE_TAG:-frontiercs/generals-io-bot-judge:experimental-${SHORT}}"

docker build \
  --build-arg GENERALS_BOTS_COMMIT="$COMMIT" \
  -f "$TASK_DIR/docker/agent/Dockerfile" \
  -t "$AGENT_TAG" \
  "$TASK_DIR"

docker build \
  --build-arg GENERALS_BOTS_COMMIT="$COMMIT" \
  -f "$TASK_DIR/docker/judge/Dockerfile" \
  -t "$JUDGE_TAG" \
  "$TASK_DIR"

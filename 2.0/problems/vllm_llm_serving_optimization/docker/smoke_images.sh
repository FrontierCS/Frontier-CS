#!/usr/bin/env bash
set -euo pipefail

AGENT_TAG="${AGENT_TAG:-frontiercs/vllm-serving-optimization-agent:experimental-v0.11.0}"
JUDGE_TAG="${JUDGE_TAG:-frontiercs/vllm-serving-optimization-judge:experimental-v0.11.0}"

echo "[agent] checking $AGENT_TAG"
docker run --rm "$AGENT_TAG" sh -lc '
  test -d /app/vllm/.git
  git -C /app/vllm rev-parse HEAD >/dev/null
  test -f /opt/serving_eval/__init__.py
  python3 -c "import sys; sys.path.insert(0, \"/opt\"); import serving_eval; print(serving_eval.__version__)"
  python3 -c "import modal, openai, datasets"
'

echo "[judge] checking $JUDGE_TAG"
docker run --rm "$JUDGE_TAG" sh -lc '
  test -d /opt/vllm-clean/.git
  git -C /opt/vllm-clean rev-parse HEAD >/dev/null
  test -f /opt/serving_eval/__init__.py
  python3 -c "import sys; sys.path.insert(0, \"/opt\"); import serving_eval; print(serving_eval.__version__)"
  python3 -c "import modal, openai, datasets, swebench"
  command -v docker >/dev/null
'

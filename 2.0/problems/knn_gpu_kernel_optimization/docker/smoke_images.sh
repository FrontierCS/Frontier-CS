#!/usr/bin/env bash
# Import-only smoke test for the built images (no GPU / Modal required).
set -euo pipefail

AGENT_TAG=${AGENT_TAG:-frontiercs/knn-gpu-kernel-optimization-agent:experimental-v0.2.0}
JUDGE_TAG=${JUDGE_TAG:-frontiercs/knn-gpu-kernel-optimization-judge:experimental-v0.2.0}

echo "== agent image =="
docker run --rm -w /app "$AGENT_TAG" python3 -c \
  "import sys, modal; sys.path.insert(0, '/opt'); import flash_gpu; \
sys.path.insert(0, '/opt/knn_ref'); import refknn; \
import knnlib; print('agent ok: modal + flash_gpu + refknn + knnlib import')"

echo "== judge image =="
docker run --rm "$JUDGE_TAG" python3 -c \
  "import sys, modal; sys.path.insert(0, '/opt'); import flash_gpu; \
sys.path.insert(0, '/opt/knn_ref'); import refknn; \
sys.path.insert(0, '/opt/knnlib-clean'); import knnlib; \
print('judge ok: modal + flash_gpu + refknn + knnlib import')"

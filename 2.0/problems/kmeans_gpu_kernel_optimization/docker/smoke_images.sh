#!/usr/bin/env bash
# Import-only smoke test for the built images (no GPU / Modal required).
set -euo pipefail

AGENT_TAG=${AGENT_TAG:-frontiercs/kmeans-gpu-kernel-optimization-agent:experimental-v0.2.0}
JUDGE_TAG=${JUDGE_TAG:-frontiercs/kmeans-gpu-kernel-optimization-judge:experimental-v0.2.0}

echo "== agent image =="
docker run --rm -w /app "$AGENT_TAG" python3 -c \
  "import sys, modal; sys.path.insert(0, '/opt'); import flash_gpu; \
sys.path.insert(0, '/opt/kmeans_ref'); import refkmeans; \
import kmeanslib; print('agent ok: modal + flash_gpu + refkmeans + kmeanslib import')"

echo "== judge image =="
docker run --rm "$JUDGE_TAG" python3 -c \
  "import sys, modal; sys.path.insert(0, '/opt'); import flash_gpu; \
sys.path.insert(0, '/opt/kmeans_ref'); import refkmeans; \
sys.path.insert(0, '/opt/kmeanslib-clean'); import kmeanslib; \
print('judge ok: modal + flash_gpu + refkmeans + kmeanslib import')"

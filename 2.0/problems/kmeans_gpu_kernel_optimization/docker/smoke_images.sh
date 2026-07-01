#!/usr/bin/env bash
# Import-only smoke test for the built images (no GPU required).
set -euo pipefail

AGENT_TAG=${AGENT_TAG:-frontiercs/kmeans-gpu-kernel-optimization-agent:experimental-v0.1.0}
JUDGE_TAG=${JUDGE_TAG:-frontiercs/kmeans-gpu-kernel-optimization-judge:experimental-v0.1.0}

echo "== agent image =="
docker run --rm -w /app "$AGENT_TAG" python3 -c \
  "import torch, triton, kmeanslib; print('agent ok: kmeanslib', kmeanslib.__version__)"

echo "== judge image =="
docker run --rm "$JUDGE_TAG" python3 -c \
  "import sys, torch, triton; \
sys.path.insert(0, '/opt/kmeans_ref'); import refkmeans; \
sys.path.insert(0, '/opt/kmeanslib-clean'); import kmeanslib; \
print('judge ok: refkmeans + kmeanslib import')"

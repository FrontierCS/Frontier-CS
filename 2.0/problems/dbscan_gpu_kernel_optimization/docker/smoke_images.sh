#!/usr/bin/env bash
# Import-only smoke test for the built images (no GPU / Modal required).
set -euo pipefail

AGENT_TAG=${AGENT_TAG:-frontiercs/dbscan-gpu-kernel-optimization-agent:experimental-v0.2.0}
JUDGE_TAG=${JUDGE_TAG:-frontiercs/dbscan-gpu-kernel-optimization-judge:experimental-v0.2.0}

echo "== agent image =="
docker run --rm -w /app "$AGENT_TAG" python3 -c \
  "import sys, modal; sys.path.insert(0, '/opt'); import flash_gpu; \
sys.path.insert(0, '/opt/dbscan_ref'); import refdbscan; \
import dbscanlib; print('agent ok: modal + flash_gpu + refdbscan + dbscanlib import')"

echo "== judge image =="
docker run --rm "$JUDGE_TAG" python3 -c \
  "import sys, modal; sys.path.insert(0, '/opt'); import flash_gpu; \
sys.path.insert(0, '/opt/dbscan_ref'); import refdbscan; \
sys.path.insert(0, '/opt/dbscanlib-clean'); import dbscanlib; \
print('judge ok: modal + flash_gpu + refdbscan + dbscanlib import')"

#!/usr/bin/env bash
# Import-only smoke test for the built images (no GPU / Modal required).
set -euo pipefail

AGENT_TAG=${AGENT_TAG:-frontiercs/ivf-pq-gpu-kernel-optimization-agent:experimental-v0.1.0}
JUDGE_TAG=${JUDGE_TAG:-frontiercs/ivf-pq-gpu-kernel-optimization-judge:experimental-v0.1.0}

echo "== agent image =="
docker run --rm -w /app "$AGENT_TAG" python3 -c \
  "import sys, modal; sys.path.insert(0, '/opt'); import flash_gpu; \
sys.path.insert(0, '/opt/ivfpq_ref'); import refivfpq; \
import ivfpqlib; print('agent ok: modal + flash_gpu + refivfpq + ivfpqlib import')"

echo "== judge image =="
docker run --rm "$JUDGE_TAG" python3 -c \
  "import sys, modal; sys.path.insert(0, '/opt'); import flash_gpu; \
sys.path.insert(0, '/opt/ivfpq_ref'); import refivfpq; \
sys.path.insert(0, '/opt/ivfpqlib-clean'); import ivfpqlib; \
print('judge ok: modal + flash_gpu + refivfpq + ivfpqlib import')"

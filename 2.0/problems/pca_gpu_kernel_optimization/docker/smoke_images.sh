#!/usr/bin/env bash
# Import-only smoke test for the built images (no GPU required).
set -euo pipefail

AGENT_TAG=${AGENT_TAG:-frontiercs/pca-gpu-kernel-optimization-agent:experimental-v0.1.0}
JUDGE_TAG=${JUDGE_TAG:-frontiercs/pca-gpu-kernel-optimization-judge:experimental-v0.1.0}

echo "== agent image =="
docker run --rm -w /app "$AGENT_TAG" python3 -c \
  "import torch, triton, pcalib; print('agent ok: pcalib', pcalib.__version__)"

echo "== judge image =="
docker run --rm "$JUDGE_TAG" python3 -c \
  "import sys, torch, triton; \
sys.path.insert(0, '/opt/pca_ref'); import refpca; \
sys.path.insert(0, '/opt/pcalib-clean'); import pcalib; \
print('judge ok: refpca + pcalib import')"

#!/usr/bin/env bash
# Build the experimental agent + judge images for knn_gpu_kernel_optimization.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)   # the problem directory (build context)

AGENT_TAG=${AGENT_TAG:-frontiercs/knn-gpu-kernel-optimization-agent:experimental-v0.5.0}
JUDGE_TAG=${JUDGE_TAG:-frontiercs/knn-gpu-kernel-optimization-judge:experimental-v0.5.0}

echo "Building agent image: $AGENT_TAG"
docker build -f "$HERE/docker/agent/Dockerfile" -t "$AGENT_TAG" "$HERE"

echo "Building judge image: $JUDGE_TAG"
docker build -f "$HERE/docker/judge/Dockerfile" -t "$JUDGE_TAG" "$HERE"

echo "Built:"
echo "  $AGENT_TAG"
echo "  $JUDGE_TAG"

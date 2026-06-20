#!/usr/bin/env bash
# Build the experimental judge image for vector_db_ann_disk. The image build
# constructs the SIFT100M benchmark data from scratch (real BIGANN download +
# DiskANN index build + baseline) and bakes it in — no manual download, no
# hosting. Run before a local Harbor trial:
#
#   bash 2.0/problems/vector_db_ann_disk/docker/build_images.sh
#
# Full scale (N=100M) is network/RAM/time heavy. For a quick smoke image:
#   N=100000 Q=1000 bash build_images.sh
#
# The agent image is the default ubuntu:24.04 (the agent needs no hidden data),
# so only the judge image is custom — see config.yaml `runtime.docker`.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
JUDGE_TAG="${JUDGE_TAG:-frontiercs/vector-db-ann-disk-judge:experimental-v1}"
N="${N:-100000000}"
Q="${Q:-10000}"

echo "Building judge image: $JUDGE_TAG  (N=$N Q=$Q)"
docker build \
    -f "$SCRIPT_DIR/judge/Dockerfile" \
    --build-arg N="$N" \
    --build-arg Q="$Q" \
    -t "$JUDGE_TAG" \
    "$SCRIPT_DIR"

echo "done: $JUDGE_TAG"

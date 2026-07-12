#!/usr/bin/env bash
set -euo pipefail

ROCKSDB_COMMIT="${ROCKSDB_COMMIT:-4595a5e95ae8525c42e172a054435782b3479c57}"
ROCKSDB_ARCHIVE_SHA256="${ROCKSDB_ARCHIVE_SHA256:-9469e7d24644e298134d0464ec2d398a9b91cc401102009ec1ecde0383485d6c}"
ROCKSDB_BUILD_JOBS="${ROCKSDB_BUILD_JOBS:-3}"
JUDGE_TAG="${JUDGE_TAG:-frontiercs/rocksdb-native-compaction-judge:experimental-v10.10.1-task2}"
PUSH_IMAGE="${PUSH_IMAGE:-0}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
PROBLEM_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

BUILD_ARGS=(
  --build-arg "ROCKSDB_COMMIT=${ROCKSDB_COMMIT}" \
  --build-arg "ROCKSDB_ARCHIVE_SHA256=${ROCKSDB_ARCHIVE_SHA256}" \
  --build-arg "ROCKSDB_BUILD_JOBS=${ROCKSDB_BUILD_JOBS}" \
  -f "${PROBLEM_DIR}/docker/judge/Dockerfile" \
  -t "${JUDGE_TAG}" \
  "${PROBLEM_DIR}"
)

if [[ "${PUSH_IMAGE}" == 1 ]]; then
  docker buildx build --platform "${PLATFORMS}" --push "${BUILD_ARGS[@]}"
  echo "Published ${JUDGE_TAG} for ${PLATFORMS}"
else
  DOCKER_BUILDKIT=1 docker build "${BUILD_ARGS[@]}"
  echo "Built ${JUDGE_TAG} for the local platform"
fi

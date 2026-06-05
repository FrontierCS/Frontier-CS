#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TASK_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

DUCKDB_REF="${DUCKDB_REF:-v1.5.3}"
DUCKDB_BUILD_JOBS="${DUCKDB_BUILD_JOBS:-1}"
AGENT_TAG="${AGENT_TAG:-frontiercs/duckdb-e2e-query-optimization-agent:experimental-v1.5.3}"
JUDGE_TAG="${JUDGE_TAG:-frontiercs/duckdb-e2e-query-optimization-judge:experimental-v1.5.3}"

docker build \
  --build-arg "DUCKDB_REF=$DUCKDB_REF" \
  -t "$AGENT_TAG" \
  "$TASK_DIR/docker/agent"

docker build \
  --build-arg "DUCKDB_REF=$DUCKDB_REF" \
  --build-arg "DUCKDB_BUILD_JOBS=$DUCKDB_BUILD_JOBS" \
  -t "$JUDGE_TAG" \
  "$TASK_DIR/docker/judge"

echo "Built:"
echo "  $AGENT_TAG"
echo "  $JUDGE_TAG"

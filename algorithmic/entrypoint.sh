#!/usr/bin/env bash
set -euo pipefail

# Set defaults for parallelism if not provided
: "${GJ_PARALLELISM:=$(nproc)}"
: "${JUDGE_WORKERS:=$(nproc)}"
export GJ_PARALLELISM JUDGE_WORKERS

echo "[entrypoint] GJ_PARALLELISM=${GJ_PARALLELISM}, JUDGE_WORKERS=${JUDGE_WORKERS}"

# Start go-judge (sandbox)
/usr/local/bin/go-judge -parallelism "${GJ_PARALLELISM}" &
sleep 0.5
# Start orchestrator
node /app/server.js

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [[ $# -gt 0 ]]; then
  exec python3 "$SCRIPT_DIR/evaluator.py" "$@"
fi

SOLUTION="/work/execution_env/solution_env/solution.rs"
if [[ ! -f "$SOLUTION" ]]; then
  echo "Error: Missing $SOLUTION" >&2
  exit 1
fi

if ! command -v cargo >/dev/null 2>&1 || ! python3 -c 'import numpy, faiss' >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends \
    build-essential cargo rustc python3-pip python3-numpy >/dev/null
  python3 -c 'import faiss' >/dev/null 2>&1 || \
    pip3 install --break-system-packages -q faiss-cpu
fi

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT
cp -R "$SCRIPT_DIR/harbor/app/." "$WORKDIR/"
cp "$SOLUTION" "$WORKDIR/src/db.rs"

# The repository validator checks that the evaluator path works; the full
# 1M-vector benchmark is exercised through Harbor.
export FRONTIER_VECTOR_DB_N="${FRONTIER_VECTOR_DB_N:-5000}"
export FRONTIER_VECTOR_DB_Q="${FRONTIER_VECTOR_DB_Q:-16}"
export FRONTIER_VECTOR_DB_WARMUP="${FRONTIER_VECTOR_DB_WARMUP:-4}"
export FRONTIER_VECTOR_DB_BATCH_SIZE="${FRONTIER_VECTOR_DB_BATCH_SIZE:-500}"
export FRONTIER_VECTOR_DB_CACHE="${FRONTIER_VECTOR_DB_CACHE:-/tmp/frontier_vector_db_ann_ci}"

python3 "$SCRIPT_DIR/evaluator.py" "$WORKDIR"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Docker runner places solution at /work/execution_env/solution_env/solution.py
# From variant dir: /work/research/problems/cant_be_late/{variant}/ -> /work/execution_env/
EXEC_ROOT="/work/execution_env"
mkdir -p "$EXEC_ROOT/solution_env"

if [[ ! -f "$EXEC_ROOT/solution_env/solution.py" ]]; then
  echo "Error: Missing $EXEC_ROOT/solution_env/solution.py" >&2
  exit 1
fi

"$SCRIPT_DIR/run_evaluator.sh"

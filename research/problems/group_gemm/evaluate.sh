#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
EXEC_ROOT=$(cd "/work/execution_env" && pwd 2>/dev/null || true)
if [[ -z "$EXEC_ROOT" ]]; then
  echo "Error: execution_env directory not found." >&2
  exit 1
fi

if [[ ! -f "$EXEC_ROOT/solution_env/solution.py" ]]; then
  echo "Error: Missing $EXEC_ROOT/solution_env/solution.py" >&2
  exit 1
fi

"$SCRIPT_DIR/run_evaluator.sh"



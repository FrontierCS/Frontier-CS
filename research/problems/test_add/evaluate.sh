#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
EXEC_ROOT="/work/execution_env"
SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"

if [[ ! -f "$SOLUTION_PATH" ]]; then
  echo "Error: Missing $SOLUTION_PATH" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/evaluator.py" "$SOLUTION_PATH"

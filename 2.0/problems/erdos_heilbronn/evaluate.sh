#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SOLUTION="/work/execution_env/solution_env/solution.py"

if [[ ! -f "$SOLUTION" ]]; then
  echo "Error: Missing $SOLUTION" >&2
  exit 1
fi

python "$SCRIPT_DIR/evaluator.py" "$SOLUTION"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [[ $# -gt 0 ]]; then
  exec python3 "$SCRIPT_DIR/evaluator.py" "$@"
fi

SOLUTION="/work/execution_env/solution_env/solution.patch"
if [[ ! -f "$SOLUTION" ]]; then
  echo "Error: Missing $SOLUTION" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/evaluator.py" "$SOLUTION"

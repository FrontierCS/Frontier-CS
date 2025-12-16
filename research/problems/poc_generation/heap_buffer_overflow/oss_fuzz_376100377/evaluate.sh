#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
EXEC_ROOT="/work/execution_env"
if [[ ! -d "$EXEC_ROOT" ]]; then
  echo "Error: execution_env directory not found at $EXEC_ROOT" >&2
  exit 1
fi

SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"
if [[ ! -f "$SOLUTION_PATH" ]]; then
  echo "Error: Missing $SOLUTION_PATH" >&2
  exit 1
fi

cd "$SCRIPT_DIR"
python3 evaluator.py --solution "$SOLUTION_PATH" --out results.json 2>&1

# Output final score from results.json as the very last line
python3 -c "import json; print(json.load(open('results.json')).get('score', 0))"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
EXEC_ROOT="/work/execution_env"
SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"
VENV_DIR="$EXEC_ROOT/.venv_symbolic_regression"
OUTPUT_PATH="$SCRIPT_DIR/result.json"

if [[ ! -f "$SOLUTION_PATH" ]]; then
  echo "Error: expected solution at $SOLUTION_PATH" >&2
  exit 1
fi

if [[ -d "$VENV_DIR" ]]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "[symbolic_regression evaluate] Warning: virtual environment not found at $VENV_DIR; using system Python" >&2
fi

python "$SCRIPT_DIR/evaluator.py" \
  --solution-path "$SOLUTION_PATH" \
  --data-dir "$SCRIPT_DIR/resources/data" \
  --reference-path "$SCRIPT_DIR/resources/reference_metrics.json" \
  --output-path "$OUTPUT_PATH"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  deactivate
fi

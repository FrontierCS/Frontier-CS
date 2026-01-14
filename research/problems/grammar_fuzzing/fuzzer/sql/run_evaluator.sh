#!/usr/bin/env bash
set -euo pipefail

# run_evaluator.sh for grammar_fuzzing/sql_fuzzer

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

EXEC_ROOT="/work/execution_env"
VENV_DIR="/work/.venv"

echo "[run_evaluator] Current directory: $(pwd)" >&2
echo "[run_evaluator] EXEC_ROOT: $EXEC_ROOT" >&2
echo "[run_evaluator] VENV_DIR: $VENV_DIR" >&2

# Activate venv if available
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  echo "[run_evaluator] Activating venv..." >&2
  source "$VENV_DIR/bin/activate"
else
  echo "[run_evaluator] WARNING: venv not found at $VENV_DIR/bin/activate" >&2
fi

# Solution path
SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"
echo "[run_evaluator] Looking for solution at: $SOLUTION_PATH" >&2
if [[ ! -f "$SOLUTION_PATH" ]]; then
  echo "[run_evaluator] ERROR: solution.py not found at $SOLUTION_PATH" >&2
  ls -la "$EXEC_ROOT" >&2 || true
  if [[ -d "$EXEC_ROOT/solution_env" ]]; then
    echo "[run_evaluator] Contents of solution_env:" >&2
    ls -la "$EXEC_ROOT/solution_env" >&2 || true
  fi
  echo '{"score": 0.0, "runs_successfully": 0.0, "error": "solution.py not found"}' > results.json
  exit 0
fi

echo "[run_evaluator] Running evaluator with solution: $SOLUTION_PATH" >&2
python3 evaluator.py --solution "$SOLUTION_PATH" --out results.json

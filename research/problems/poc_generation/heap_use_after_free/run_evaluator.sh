#!/usr/bin/env bash
echo "DEBUG: run_evaluator.sh started!" >&2
set -euo pipefail

PROBLEM_DIR=$(pwd)
EXEC_ROOT="/work/execution_env"
VENV_DIR="$EXEC_ROOT/.venv"

echo "[run_evaluator] Current directory: $PROBLEM_DIR" >&2
echo "[run_evaluator] EXEC_ROOT: $EXEC_ROOT" >&2
echo "[run_evaluator] VENV_DIR: $VENV_DIR" >&2

if [[ -f "$VENV_DIR/bin/activate" ]]; then
  echo "[run_evaluator] Activating venv..." >&2
  source "$VENV_DIR/bin/activate"
else
  echo "[run_evaluator] WARNING: venv missing at $VENV_DIR/bin/activate" >&2
fi

SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"
if [[ ! -f "$SOLUTION_PATH" ]]; then
  echo "[run_evaluator] ERROR: solution.py not found at $SOLUTION_PATH" >&2
  exit 1
fi
echo "[run_evaluator] Using solution: $SOLUTION_PATH" >&2

RESULTS_JSON="results.json"
EVAL_LOG="evaluation.log"

echo "[run_evaluator] Running evaluator..." >&2
if ! python3 evaluator.py \
  --solution "$SOLUTION_PATH" \
  --out "$RESULTS_JSON" \
  2>&1 | tee "$EVAL_LOG"; then
  echo "[run_evaluator] ERROR: evaluator.py failed" >&2
  exit 1
fi

echo "[run_evaluator] Results written to $RESULTS_JSON" >&2
echo "[run_evaluator] Log written to $EVAL_LOG" >&2

# Output final score from results.json as the very last line (for main_loop.sh)
python3 -c "import json; print(json.load(open('$RESULTS_JSON')).get('score', 0))"

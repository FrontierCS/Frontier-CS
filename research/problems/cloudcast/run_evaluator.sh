#!/usr/bin/env bash
echo "DEBUG: run_evaluator.sh started!" >&2
set -euo pipefail

EXEC_ROOT="/work/execution_env"
VENV_DIR="$EXEC_ROOT/.venv"

echo "[run_evaluator] EXEC_ROOT: $EXEC_ROOT" >&2
echo "[run_evaluator] VENV_DIR: $VENV_DIR" >&2

if [[ -f "$VENV_DIR/bin/activate" ]]; then
  echo "[run_evaluator] Activating venv..." >&2
  source "$VENV_DIR/bin/activate"
else
  echo "[run_evaluator] WARNING: venv not found, continuing with system Python" >&2
fi

SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"
if [[ ! -f "$SOLUTION_PATH" ]]; then
  echo "[run_evaluator] ERROR: solution.py not found at $SOLUTION_PATH" >&2
  exit 1
fi

RESULTS_JSON="results.json"
EVAL_LOG="evaluation.log"

echo "[run_evaluator] Running Cloudcast evaluator..." >&2
if ! python3 evaluator.py \
  --solution "$SOLUTION_PATH" \
  --spec "resources/submission_spec.json" \
  --out "$RESULTS_JSON" \
  2>&1 | tee "$EVAL_LOG"; then
  echo "[run_evaluator] ERROR: evaluator.py failed" >&2
  exit 1
fi

echo "[run_evaluator] Results written to $RESULTS_JSON" >&2
echo "[run_evaluator] Log written to $EVAL_LOG" >&2

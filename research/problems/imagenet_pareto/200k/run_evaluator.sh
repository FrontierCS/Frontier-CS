#!/usr/bin/env bash
echo "DEBUG: run_evaluator.sh started!" >&2
set -euo pipefail

PROBLEM_DIR=$(pwd)
EXEC_ROOT="/work/execution_env"
VENV_DIR="$EXEC_ROOT/.venv"

echo "[run_evaluator] Current directory: $PROBLEM_DIR" >&2
echo "[run_evaluator] EXEC_ROOT: $EXEC_ROOT" >&2
echo "[run_evaluator] VENV_DIR: $VENV_DIR" >&2

# Debug: check if execution_env exists and what's in it
if [[ -d "$EXEC_ROOT" ]]; then
  echo "[run_evaluator] DEBUG: $EXEC_ROOT exists" >&2
  if [[ -d "$EXEC_ROOT/solution_env" ]]; then
    echo "[run_evaluator] DEBUG: $EXEC_ROOT/solution_env exists, contents:" >&2
    ls -la "$EXEC_ROOT/solution_env/" >&2
  else
    echo "[run_evaluator] DEBUG: $EXEC_ROOT/solution_env DOES NOT EXIST" >&2
  fi
else
  echo "[run_evaluator] DEBUG: $EXEC_ROOT DOES NOT EXIST" >&2
fi

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

echo "[run_evaluator] Running ImageNet Pareto evaluator..." >&2
if ! python3 evaluator.py \
  --solution "$SOLUTION_PATH" \
  --out "$RESULTS_JSON" \
  2>&1 | tee "$EVAL_LOG"; then
  echo "[run_evaluator] ERROR: evaluator.py failed" >&2
  exit 1
fi

echo "[run_evaluator] Results written to $RESULTS_JSON" >&2
echo "[run_evaluator] Log written to $EVAL_LOG" >&2

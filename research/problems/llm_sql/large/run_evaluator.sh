#!/usr/bin/env bash
set -euo pipefail

# run_evaluator.sh for llm_sql_large

PROBLEM_DIR=$(pwd)
EXEC_ROOT="/work/execution_env"
VENV_DIR="$EXEC_ROOT/.venv"

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
  echo "[run_evaluator] Contents of $EXEC_ROOT:" >&2
  ls -la "$EXEC_ROOT" >&2 || true
  if [[ -d "$EXEC_ROOT/solution_env" ]]; then
    echo "[run_evaluator] Contents of $EXEC_ROOT/solution_env:" >&2
    ls -la "$EXEC_ROOT/solution_env" >&2 || true
  fi
  exit 1
fi

RESULTS_JSON="results.json"
EVAL_LOG="evaluation.log"

echo "[run_evaluator] Running LLM_SQL_LARGE evaluator..." >&2
if ! python3 evaluator.py \
  --solution "$SOLUTION_PATH" \
  --out "$RESULTS_JSON" \
  2>&1 | tee "$EVAL_LOG"; then
  echo "[run_evaluator] ERROR: evaluator.py failed!" >&2
  exit 1
fi

echo "[run_evaluator] Results written to $RESULTS_JSON" >&2
echo "[run_evaluator] Log written to $EVAL_LOG" >&2



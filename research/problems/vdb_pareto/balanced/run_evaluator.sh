#!/usr/bin/env bash
echo "DEBUG: run_evaluator.sh started!" >&2
set -euo pipefail

# run_evaluator.sh for vdb_design
# Thin wrapper that calls evaluator.py with standardized arguments

PROBLEM_DIR=$(pwd)
EXEC_ROOT="/work/execution_env"
VENV_DIR="$EXEC_ROOT/.venv"

echo "[run_evaluator] Current directory: $(pwd)" >&2
echo "[run_evaluator] EXEC_ROOT: $EXEC_ROOT" >&2
echo "[run_evaluator] VENV_DIR: $VENV_DIR" >&2

# Activate venv
if [[ -f "$VENV_DIR/bin/activate" ]]; then
  echo "[run_evaluator] Activating venv..." >&2
  source "$VENV_DIR/bin/activate"
else
  echo "[run_evaluator] WARNING: venv not found at $VENV_DIR/bin/activate" >&2
  echo "[run_evaluator] DEBUG: Listing $EXEC_ROOT:" >&2
  ls -la "$EXEC_ROOT" >&2 || echo "[run_evaluator] ERROR: Can't list $EXEC_ROOT" >&2
  if [[ -d "$VENV_DIR" ]]; then
    echo "[run_evaluator] DEBUG: Listing $VENV_DIR:" >&2
    ls -la "$VENV_DIR" >&2 || echo "[run_evaluator] ERROR: Can't list $VENV_DIR" >&2
    if [[ -d "$VENV_DIR/bin" ]]; then
      echo "[run_evaluator] DEBUG: Listing $VENV_DIR/bin:" >&2
      ls -la "$VENV_DIR/bin" >&2 || echo "[run_evaluator] ERROR: Can't list $VENV_DIR/bin" >&2
    fi
  else
    echo "[run_evaluator] DEBUG: $VENV_DIR does not exist" >&2
  fi
fi

# Solution path - copied by main_loop.sh to execution_env
SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"
echo "[run_evaluator] Looking for solution at: $SOLUTION_PATH" >&2
if [[ ! -f "$SOLUTION_PATH" ]]; then
  echo "[run_evaluator] ERROR: solution.py not found at $SOLUTION_PATH" >&2
  echo "[run_evaluator] Contents of $EXEC_ROOT:" >&2
  ls -la "$EXEC_ROOT" >&2
  if [[ -d "$EXEC_ROOT/solution_env" ]]; then
    echo "[run_evaluator] Contents of $EXEC_ROOT/solution_env:" >&2
    ls -la "$EXEC_ROOT/solution_env" >&2
  fi
  exit 1
fi

# Output paths
RESULTS_JSON="results.json"
EVAL_LOG="evaluation.log"

# Call evaluator
echo "[run_evaluator] Running VDB Design evaluator..." >&2
python3 evaluator.py \
  --solution "$SOLUTION_PATH" \
  --out "$RESULTS_JSON" \
  2>&1 | tee "$EVAL_LOG"
EVAL_EXIT_CODE=${PIPESTATUS[0]}

echo "[run_evaluator] evaluator.py exit code: $EVAL_EXIT_CODE" >&2

if [[ $EVAL_EXIT_CODE -ne 0 ]]; then
  echo "[run_evaluator] ERROR: evaluator.py failed with exit code $EVAL_EXIT_CODE!" >&2
  exit $EVAL_EXIT_CODE
fi

echo "[run_evaluator] Results written to $RESULTS_JSON" >&2
echo "[run_evaluator] Log written to $EVAL_LOG" >&2
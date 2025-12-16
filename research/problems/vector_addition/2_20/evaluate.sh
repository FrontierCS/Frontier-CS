#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

EXEC_ROOT="/work/execution_env"
SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"

# Check if solution exists
if [[ ! -f "$SOLUTION_PATH" ]]; then
    echo "ERROR: solution.py not found at $SOLUTION_PATH" >&2
    exit 1
fi

# Run the evaluator
python3 evaluator.py --solution-path "$SOLUTION_PATH" --output-path ./result.json

# Check if evaluation succeeded
if [ ! -f "./result.json" ]; then
    echo "Evaluation failed - no result file generated"
    exit 1
fi

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

EXEC_ROOT="/work/execution_env"
SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"

# Run the evaluator
python3 evaluator.py --solution-path "$SOLUTION_PATH" --output-path ./result.json

# Check if evaluation succeeded
if [ ! -f "./result.json" ]; then
    echo "Evaluation failed - no result file generated"
    exit 1
fi

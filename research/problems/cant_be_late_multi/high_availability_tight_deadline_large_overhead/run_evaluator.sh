#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Use /work/execution_env in Docker, or local execution_env for manual runs
EXEC_ROOT="/work/execution_env"

# Use system python3 (framework installs deps with uv pip install --system)
PYBIN="python3"

SOLUTION_PATH="$EXEC_ROOT/solution_env/solution.py"
SPEC_PATH="$SCRIPT_DIR/resources/submission_spec.json"
OUTPUT_JSON=$(CBL_LOG_LEVEL=WARNING "$PYBIN" "$SCRIPT_DIR/evaluator.py" --solution "$SOLUTION_PATH" --spec "$SPEC_PATH")
SCORE=$(python3 - <<'PY' "$OUTPUT_JSON"
import json, sys
payload = json.loads(sys.argv[1])
print(payload.get("combined_score", payload.get("score", 0)))
PY
)

echo "$OUTPUT_JSON" > "$EXEC_ROOT/evaluator_output.json"
echo "$SCORE"

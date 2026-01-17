#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Use system python3 (framework installs deps with uv pip install --system)
PYBIN="python3"

# Docker runner places solution at /work/execution_env/solution_env/solution.py
SOLUTION_PATH="/work/execution_env/solution_env/solution.py"
SPEC_PATH="$SCRIPT_DIR/resources/submission_spec.json"

OUTPUT_JSON=$(CBL_LOG_LEVEL=WARNING "$PYBIN" "$SCRIPT_DIR/evaluator.py" --solution "$SOLUTION_PATH" --spec "$SPEC_PATH")
SCORE=$(python3 - <<'PY' "$OUTPUT_JSON"
import json, sys
payload = json.loads(sys.argv[1])
print(payload.get("score", 0))
PY
)

echo "$OUTPUT_JSON" > "$SCRIPT_DIR/evaluator_output.json"
echo "$SCORE"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [[ $# -gt 0 ]]; then
  exec python3 "$SCRIPT_DIR/evaluator.py" "$1"
fi

for candidate in \
  /work/execution_env/solution_env/solution.patch \
  /work/execution_env/solution_env/solution.cpp; do
  if [[ -f "$candidate" ]]; then
    exec python3 "$SCRIPT_DIR/evaluator.py" "$candidate"
  fi
done

echo "Error: solution artifact is missing" >&2
exit 1

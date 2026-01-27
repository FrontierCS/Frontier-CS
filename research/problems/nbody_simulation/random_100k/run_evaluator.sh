#!/usr/bin/env bash
# Helper script to run evaluator locally for testing
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

SOLUTION_PATH="${1:-./solution.cpp}"

python3 evaluator.py --solution-path "$SOLUTION_PATH" --output-path ./result.json

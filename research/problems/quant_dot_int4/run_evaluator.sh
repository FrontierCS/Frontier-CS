#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

# Run the evaluator with proper arguments
python3 evaluator.py \
    --solution-path ./solution.py \
    --spec-path ./resources/submission_spec.json \
    --output-path ./result.json

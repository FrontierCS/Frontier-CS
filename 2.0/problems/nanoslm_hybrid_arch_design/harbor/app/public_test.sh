#!/usr/bin/env bash
# Static policy gate -- the judge's exact rules. Fast, no GPU, no training.
set -euo pipefail
exec python3 /app/public_test.py "${1:-/app/model.py}"

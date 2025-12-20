#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TARGET_DIR="/work/Frontier-CS/execution_env/solution_env"
mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/resources/solution.py" "$TARGET_DIR/solution.py"
echo "[gpt5.1_cant_be_late_low_availability_tight_deadline_small_overhead_1] solution.py staged"

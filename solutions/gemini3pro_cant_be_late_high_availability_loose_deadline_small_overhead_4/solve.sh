#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TARGET_DIR="/work/Frontier-CS/execution_env/solution_env"
mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/resources/solution.py" "$TARGET_DIR/solution.py"
echo "[gemini3pro_cant_be_late_high_availability_loose_deadline_small_overhead_4] solution.py staged"

#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TARGET_DIR="/work/Frontier-CS/execution_env/solution_env"
mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/resources/solution.py" "$TARGET_DIR/solution.py"
echo "[grok4fastreasoning_poc_generation_heap_buffer_overflow_oss_fuzz_42536108_4] solution.py staged"

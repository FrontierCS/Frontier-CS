#!/usr/bin/env bash
# Local CLI evaluation for nanowm_rollout_speedup.
# Full runs need a GPU (local backend) or Modal credentials, plus the baked
# NanoWM assets (FRONTIER_NWM_* env, see speedup_eval/settings.py). Without a GPU
# this falls back to the smoke path (patch-policy validation only), which is what
# repository CI exercises.
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export FRONTIER_NWM_PKG="${FRONTIER_NWM_PKG:-$SCRIPT_DIR}"
if ! python3 -c 'import torch; assert torch.cuda.is_available()' >/dev/null 2>&1; then
  export FRONTIER_NWM_SMOKE="${FRONTIER_NWM_SMOKE:-1}"
fi
SOLUTION="${1:-$SCRIPT_DIR/reference.patch}"
exec python3 "$SCRIPT_DIR/evaluator.py" "$SOLUTION"

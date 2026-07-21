#!/usr/bin/env bash
# Local CLI wrapper for non-Harbor evaluation.
#
# Usage:
#   bash evaluate.sh /path/to/model.py     # score a submission (needs torch+GPU)
#   bash evaluate.sh --selftest            # torch-free policy/scoring/fingerprint tests
#
# Tip: FRONTIER_NANOSLM_SMOKE=1 shrinks the model/budget for a fast CPU wiring
# check (never used for real scoring).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARG="${1:-}"

if [[ -z "${ARG}" ]]; then
  ARG="${HERE}/reference.py"
fi

exec python3 "${HERE}/evaluator.py" "${ARG}"

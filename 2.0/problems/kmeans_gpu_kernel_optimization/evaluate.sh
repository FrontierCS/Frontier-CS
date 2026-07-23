#!/usr/bin/env bash
# Local CLI evaluation for kmeans_gpu_kernel_optimization.
#
# A full run needs a GPU plus the baked judge sources at /opt (the pristine
# /opt/kmeanslib-clean tree and the frozen /opt/kmeans_ref baseline; see the
# judge image). Without them the evaluator still validates the patch policy and
# returns a smoke score, which is what repository CI exercises (the reference
# patch passes the policy). Pass a patch path to score it directly.
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SOLUTION="${1:-$SCRIPT_DIR/reference.patch}"
exec python3 "$SCRIPT_DIR/evaluator.py" "$SOLUTION"

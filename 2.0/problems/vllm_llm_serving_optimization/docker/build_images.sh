#!/usr/bin/env bash
# Rebuild the vllm_llm_serving_optimization agent + judge images with the updated
# serving_eval harness (BFCL workload + 50/50 scoring + correctness fixes).
#
#   bash 2.0/problems/vllm_llm_serving_optimization/docker/build_images.sh [new_tag] [base_tag]
#
# This is an OVERLAY rebuild: it layers the refreshed /opt/serving_eval (which
# now includes bfcl.py + the vendored BFCL slice under bfcl_data/) on top of the
# existing base images, which already bake the clean vLLM v0.11.0 tree
# (/opt/vllm-clean) and the OpenAI/Modal/datasets deps. The BFCL path is
# self-contained (stdlib + openai only), so no extra pip install is required.
#
# Both images carry /opt/serving_eval: the judge runs the authoritative
# measurement, and the agent image runs the same harness for the public test.
set -euo pipefail

NEW_TAG="${1:-experimental-v0.11.1}"
BASE_TAG="${2:-experimental-v0.11.0}"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROB=$(cd "$SCRIPT_DIR/.." && pwd)

AGENT_BASE="frontiercs/vllm-serving-optimization-agent:${BASE_TAG}"
JUDGE_BASE="frontiercs/vllm-serving-optimization-judge:${BASE_TAG}"
AGENT_OUT="frontiercs/vllm-serving-optimization-agent:${NEW_TAG}"
JUDGE_OUT="frontiercs/vllm-serving-optimization-judge:${NEW_TAG}"

for img in "$AGENT_BASE" "$JUDGE_BASE"; do
  if ! docker image inspect "$img" >/dev/null 2>&1; then
    echo "ERROR: base image '$img' not found. Build the v0.11.0 base images first." >&2
    exit 1
  fi
done

CTX=$(mktemp -d); trap 'rm -rf "$CTX"' EXIT
# Stage the refreshed harness (exclude bytecode caches so no stale .pyc ships).
mkdir -p "$CTX/serving_eval"
( cd "$PROB/serving_eval" && tar --exclude='__pycache__' -cf - . ) | tar -xf - -C "$CTX/serving_eval"

# Sanity: the vendored BFCL **memory** workload assets must be present, or the
# BFCL workload would silently degrade to SWE-bench-only. The memory workload
# needs: the harness, the query data, the kv tool docs, the kv backend, and the
# 5 pre-baked per-scenario memory snapshots (frozen via build_memory_snapshots).
[ -f "$CTX/serving_eval/bfcl.py" ] || { echo "ERROR: serving_eval/bfcl.py missing" >&2; exit 1; }
[ -f "$CTX/serving_eval/bfcl_data/BFCL_v4_memory.json" ] || { echo "ERROR: vendored BFCL memory data missing" >&2; exit 1; }
[ -f "$CTX/serving_eval/bfcl_data/multi_turn_func_doc/memory_kv.json" ] || { echo "ERROR: vendored memory kv tool docs missing" >&2; exit 1; }
[ -f "$CTX/serving_eval/bfcl_vendor/memory_kv.py" ] || { echo "ERROR: vendored memory kv backend missing" >&2; exit 1; }
for s in customer healthcare finance student notetaker; do
  [ -f "$CTX/serving_eval/bfcl_data/memory_snapshots/${s}_final.json" ] || {
    echo "ERROR: pre-baked memory snapshot '${s}_final.json' missing (run build_memory_snapshots first)" >&2; exit 1; }
done

build_overlay() {
  local base="$1" out="$2"
  cat > "$CTX/Dockerfile" <<EOF
FROM ${base}
# rank-bm25 (+numpy) for the BFCL memory kv backend's *_key_search; everything
# else the memory workload needs is stdlib + openai (already present).
RUN pip3 install --break-system-packages --no-cache-dir rank-bm25 || pip install --break-system-packages --no-cache-dir rank-bm25
# Replace the baked harness with the refreshed serving_eval (BFCL memory + fixes).
RUN rm -rf /opt/serving_eval
COPY serving_eval /opt/serving_eval
# Fail the build early if the harness does not import or the vendored data +
# pre-baked memory snapshots are missing.
RUN python3 -c "import sys; sys.path.insert(0, '/opt'); import serving_eval; import serving_eval.bfcl as b; from serving_eval.bfcl_vendor.memory_kv import MemoryAPI_kv; assert b.bfcl_available(), 'BFCL memory data/snapshots not found in image'"
EOF
  docker build -t "$out" -f "$CTX/Dockerfile" "$CTX"
}

echo "==> Building agent image $AGENT_OUT (overlay on $AGENT_BASE)"
build_overlay "$AGENT_BASE" "$AGENT_OUT"
echo "==> Building judge image $JUDGE_OUT (overlay on $JUDGE_BASE)"
build_overlay "$JUDGE_BASE" "$JUDGE_OUT"

echo
echo "Built:"
echo "  $AGENT_OUT"
echo "  $JUDGE_OUT"
echo "Update config.yaml runtime.docker.{image,judge_image} to the '${NEW_TAG}' tag if you bumped it."

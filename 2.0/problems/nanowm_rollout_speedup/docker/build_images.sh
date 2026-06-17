#!/usr/bin/env bash
# Build the nanowm_rollout_speedup agent + judge images.
#   bash 2.0/problems/nanowm_rollout_speedup/docker/build_images.sh [tag]
# Requires the hidden assets staged under $NWM_ASSETS (must be set; no default):
#   $NWM_ASSETS/ckpts/nanowm-l2-csgo-100k/    (L/2 CSGO checkpoint dir -> baked as ckpts/nanowm-l2-csgo)
#   $NWM_ASSETS/csgo/1-200/*.hdf5             (held-out CSGO episode subset -> data/csgo)
#   $NWM_ASSETS/csgo_subset/{val_files.txt,val_starts.npy}   (-> data/csgo_subset)
#   (baseline is optional; computed on first trial otherwise)
set -euo pipefail
TAG="${1:-experimental-v0}"
NANOWM_COMMIT="${NANOWM_COMMIT:-main}"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROB=$(cd "$SCRIPT_DIR/.." && pwd)
NWM_ASSETS="${NWM_ASSETS:?set NWM_ASSETS to the dir holding the L/2 CSGO ckpt + held-out CSGO subset (see header)}"

CTX=$(mktemp -d); trap 'rm -rf "$CTX"' EXIT
mkdir -p "$CTX/task_ctx"
cp -r "$PROB/speedup_eval" "$CTX/task_ctx/task_pkg"
cp "$PROB/evaluator.py" "$CTX/task_ctx/evaluator.py"
cp -r "$PROB/harbor/app" "$CTX/task_ctx/harbor_app"
cp -r "$PROB/infra_patches" "$CTX/task_ctx/infra_patches" 2>/dev/null || mkdir -p "$CTX/task_ctx/infra_patches"
# judge-only hidden assets
mkdir -p "$CTX/task_ctx/assets"
cp -r "$NWM_ASSETS/ckpts/nanowm-l2-csgo-100k" "$CTX/task_ctx/assets/ckpts/nanowm-l2-csgo" 2>/dev/null || true
cp -r "$NWM_ASSETS/csgo" "$CTX/task_ctx/assets/data/csgo" 2>/dev/null || true
cp -r "$NWM_ASSETS/csgo_subset" "$CTX/task_ctx/assets/data/csgo_subset" 2>/dev/null || true

# The copies above are best-effort (|| true); fail loudly if a REQUIRED asset is
# missing so we never build a judge image with no model / no held-out data.
[ -d "$CTX/task_ctx/assets/ckpts/nanowm-l2-csgo" ] || { echo "ERROR: checkpoint missing — expected \$NWM_ASSETS/ckpts/nanowm-l2-csgo-100k" >&2; exit 1; }
[ -d "$CTX/task_ctx/assets/data/csgo" ]            || { echo "ERROR: held-out CSGO data missing — expected \$NWM_ASSETS/csgo" >&2; exit 1; }

docker build --target "" --build-arg NANOWM_COMMIT="$NANOWM_COMMIT" \
  -t "frontiercs/nanowm-rollout-speedup-agent:$TAG" -f "$SCRIPT_DIR/agent/Dockerfile" "$CTX"
docker build --build-arg NANOWM_COMMIT="$NANOWM_COMMIT" \
  -t "frontiercs/nanowm-rollout-speedup-judge:$TAG" -f "$SCRIPT_DIR/judge/Dockerfile" "$CTX"
echo "Built frontiercs/nanowm-rollout-speedup-{agent,judge}:$TAG"

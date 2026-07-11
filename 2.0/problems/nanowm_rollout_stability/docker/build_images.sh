#!/usr/bin/env bash
# Build the nanowm_rollout_stability agent + judge images.
#   bash 2.0/problems/nanowm_rollout_stability/docker/build_images.sh [tag]
# Judge-only hidden assets are AUTO-STAGED from public sources (no manual step):
#   $NWM_ASSETS/ckpts/nanowm-l2-csgo-100k/    (L/2 CSGO ckpt -> baked as ckpts/nanowm-l2-csgo)
#   $NWM_ASSETS/csgo/1-200/*.hdf5             (held-out CSGO episode subset -> data/csgo)
#   $NWM_ASSETS/csgo_subset/{val_files.txt,val_starts.npy}   (-> data/csgo_subset)
#   (baseline is optional; computed on first trial otherwise)
# NWM_ASSETS defaults to a cache dir and is populated by docker/prep_assets.py
# (downloads the public HF checkpoint + the CSGO 1-200 chunk, derives the val
# subset). Pre-stage NWM_ASSETS yourself to skip the download. Both nanowm tasks
# share an identical asset set, so a single staged dir serves both builds.
set -euo pipefail
TAG="${1:-experimental-v0}"
NANOWM_COMMIT="${NANOWM_COMMIT:-main}"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROB=$(cd "$SCRIPT_DIR/.." && pwd)
NWM_ASSETS="${NWM_ASSETS:-$HOME/.cache/frontier-cs/nwm_assets}"

# Auto-stage the public assets if not already present (self-contained build).
if [ ! -f "$NWM_ASSETS/ckpts/nanowm-l2-csgo-100k/model_state_dict.pt" ] || \
   ! ls "$NWM_ASSETS/csgo/1-200/"*.hdf5 >/dev/null 2>&1; then
  echo "Staging NanoWM assets into $NWM_ASSETS (one-time public download via prep_assets.py)..."
  uv run --no-project --with huggingface_hub --with safetensors --with torch --with numpy \
    python "$SCRIPT_DIR/prep_assets.py" --out "$NWM_ASSETS"
fi

CTX=$(mktemp -d); trap 'rm -rf "$CTX"' EXIT
mkdir -p "$CTX/task_ctx"
# Preserve the package DIRECTORY (task_pkg/stability_eval/) so the baked layout is
# /opt/nanowm/task/stability_eval/ + /opt/nanowm/task/evaluator.py. evaluator.py
# does `from stability_eval import ...` and the eval modules use relative imports
# (`from . import settings`), so flattening the contents into task/ breaks both.
mkdir -p "$CTX/task_ctx/task_pkg"
cp -r "$PROB/stability_eval" "$CTX/task_ctx/task_pkg/stability_eval"
cp "$PROB/evaluator.py" "$CTX/task_ctx/evaluator.py"
cp -r "$PROB/harbor/app" "$CTX/task_ctx/harbor_app"
cp -r "$PROB/infra_patches" "$CTX/task_ctx/infra_patches" 2>/dev/null || mkdir -p "$CTX/task_ctx/infra_patches"
# judge-only hidden assets (create dest parents first so the renaming cp lands)
mkdir -p "$CTX/task_ctx/assets/ckpts" "$CTX/task_ctx/assets/data"
cp -r "$NWM_ASSETS/ckpts/nanowm-l2-csgo-100k" "$CTX/task_ctx/assets/ckpts/nanowm-l2-csgo" 2>/dev/null || true
cp -r "$NWM_ASSETS/csgo" "$CTX/task_ctx/assets/data/csgo" 2>/dev/null || true
cp -r "$NWM_ASSETS/csgo_subset" "$CTX/task_ctx/assets/data/csgo_subset" 2>/dev/null || true

# The copies above are best-effort (|| true); fail loudly if a REQUIRED asset is
# missing so we never build a judge image with no model / no held-out data.
[ -d "$CTX/task_ctx/assets/ckpts/nanowm-l2-csgo" ] || { echo "ERROR: checkpoint missing — expected \$NWM_ASSETS/ckpts/nanowm-l2-csgo-100k" >&2; exit 1; }
[ -d "$CTX/task_ctx/assets/data/csgo" ]            || { echo "ERROR: held-out CSGO data missing — expected \$NWM_ASSETS/csgo" >&2; exit 1; }

docker build --target "" --build-arg NANOWM_COMMIT="$NANOWM_COMMIT" \
  -t "frontiercs/nanowm-rollout-stability-agent:$TAG" -f "$SCRIPT_DIR/agent/Dockerfile" "$CTX"
docker build --build-arg NANOWM_COMMIT="$NANOWM_COMMIT" \
  -t "frontiercs/nanowm-rollout-stability-judge:$TAG" -f "$SCRIPT_DIR/judge/Dockerfile" "$CTX"
echo "Built frontiercs/nanowm-rollout-stability-{agent,judge}:$TAG"

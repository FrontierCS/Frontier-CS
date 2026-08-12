#!/usr/bin/env bash
# Build the agent + judge images for nanoslm_hybrid_arch_design.
#
#   bash docker/build_images.sh [tag]
#
# NOTE ON THE THREE-IMAGE ARCHITECTURE. This script builds TWO images; a third
# is built remotely by Modal from harness/modal_app.py and is never produced
# here:
#
#   agent  (this script, CPU)  - workspace: starter model.py + the static gate
#   judge  (this script, CPU)  - dispatches to Modal, scores, holds val.bin
#   Modal  (modal deploy, GPU) - torch 2.6.0 / triton 3.2.0 / fla 0.5.1
#
# The GPU stack lives ONLY in the Modal image. Keep its pins in
# harness/modal_app.py in sync: that exact combination is
# the one whose GDN backward kernel compiles (triton 3.1.0 hung for 30+ min;
# fla 0.4.1 failed to lower the backward).
set -euo pipefail

TAG="${1:-experimental-v0}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROB="$(cd "$HERE/.." && pwd)"
ASSETS="${NANOSLM_ARCH_ASSETS:-$PROB/.assets}"
# Publishing (manual, after a successful build):
#   docker login ghcr.io -u <github-user>   # token needs write:packages on the org
#   docker push "$AGENT_IMG" && docker push "$JUDGE_IMG"
# Visibility: the AGENT package may be public; the JUDGE package must stay
# PRIVATE -- it embeds the held-out val.bin -- so pullers (Harbor infra,
# --force-build) need a token with read:packages instead.
AGENT_IMG="ghcr.io/frontiercs/nanoslm-hybrid-arch-design-agent:$TAG"
JUDGE_IMG="ghcr.io/frontiercs/nanoslm-hybrid-arch-design-judge:$TAG"

# --- assets -------------------------------------------------------------------
if [ ! -s "$ASSETS/train.bin" ] || [ ! -s "$ASSETS/val.bin" ] \
   || [ ! -s "$ASSETS/manifest.json" ]; then
  echo "[build] staging tokenized corpus into $ASSETS (cold cache)"
  NANOSLM_ARCH_ASSETS="$ASSETS" python3 "$HERE/prep_assets.py"
fi
# manifest.json is NOT optional metadata: it carries `val_bytes`, the denominator
# of the scored bits-per-byte. Without it harness/data.py raises rather than
# silently normalizing by a token count -- so a judge image built without it
# would fail every run. See docker/prep_assets.py.
for f in train.bin val.bin manifest.json; do
  [ -s "$ASSETS/$f" ] || { echo "FATAL: missing $ASSETS/$f"; exit 1; }
done
MANIFEST="$ASSETS/manifest.json" python3 - <<'PY'
import json, os, sys
m = json.load(open(os.environ["MANIFEST"]))
b, t = m.get("val_bytes", 0), m.get("val_target_tokens", 0)
if not (b > 0 and t > 0):
    sys.exit("FATAL: manifest has no positive val_bytes/val_target_tokens")
print("[check] val_bytes=%d over %d target tokens (%.2f B/tok)" % (b, t, b / t))
PY

# --- build context ------------------------------------------------------------
CTX="$(mktemp -d)"
trap 'rm -rf "$CTX"' EXIT
mkdir -p "$CTX/task_ctx/task_pkg" "$CTX/task_ctx/agent_task" "$CTX/task_ctx/assets"

cp -r "$PROB/harness"      "$CTX/task_ctx/task_pkg/harness"
cp    "$PROB/evaluator.py" "$CTX/task_ctx/evaluator.py"
cp -r "$PROB/harbor/app"   "$CTX/task_ctx/harbor_app"
cp    "$PROB/harness/policy.py" "$CTX/task_ctx/agent_task/policy.py"
cp    "$ASSETS/train.bin" "$ASSETS/val.bin" "$ASSETS/manifest.json" \
      "$CTX/task_ctx/assets/"

# modal_app.py declares the GPU image and is judge-side only; it is already in
# task_pkg via harness/. Nothing else needs to move.

# --- leak grep: what ships to the AGENT ---------------------------------------
# policy.py legitimately CONTAINS the denylist, which names the metric and
# held-out identifiers -- those strings are public by design (the readme states
# them) and are what the gate matches on. So grep for hidden VALUES and real
# PATHS, not for the denylist's own words.
POLICY="$CTX/task_ctx/agent_task/policy.py"
#
# TWO greps, not one. policy.py's DENY tuples literally contain "val.bin",
# "/opt/", "holdout" etc -- that IS the denylist, it is public by design, and a
# naive single grep fails the build on the gate's own source every time. (This
# exact trap already exists in lm_arch_discovery/docker/build_images.sh and in
# align_overopt_stability's; it is easy to re-introduce.)
#
#   (1) hidden VALUES over the whole file. These are strictly more specific
#       than anything the denylist contains, so they cannot collide with it.
#   (2) asset identifiers with the DENY tuples EXCISED, which catches a real
#       path leaking in via a default or a stray constant while letting the
#       denylist keep naming them.
# `bpb_score_scale` replaced the old `r_target`; both are matched so a stale
# checkout cannot slip the old name through this gate.
if grep -qiE "r_target|bpb_score_scale|train_seconds|param_cap|baseline_ppl|[0-9]{6,}" "$POLICY"; then
  echo "FATAL: policy.py would leak a hidden VALUE to the agent image"
  exit 1
fi
if sed -e '/^POLICY_DENY_TOKENS[A-Z_]*: tuple/,/^)/d' -e '/^[[:space:]]*#/d' "$POLICY" \
     | grep -qiE "/opt/nanoslm_arch|val\.bin"; then
  echo "FATAL: policy.py names a judge asset outside its denylist block"
  exit 1
fi
# The starter model.py must not name the held-out stream either.
if grep -qiE "/opt/nanoslm_arch|val\.bin" "$CTX/task_ctx/harbor_app/model.py"; then
  echo "FATAL: starter model.py references judge assets"; exit 1
fi

# --- build --------------------------------------------------------------------
echo "[build] agent -> $AGENT_IMG"
docker build -f "$HERE/agent/Dockerfile" -t "$AGENT_IMG" "$CTX"
echo "[build] judge -> $JUDGE_IMG"
docker build -f "$HERE/judge/Dockerfile" -t "$JUDGE_IMG" "$CTX"

# --- post-build isolation ------------------------------------------------------
echo "[check] held-out stream must be unreachable from the AGENT image"
# policy.py is EXEMPT from the content grep and only from it: its denylist
# names "val.bin" by design, which is the third place in this script where that
# distinction matters. EVERY other file under /app is grepped whole -- the loop
# enumerates with `find`, not a fixed list, so a leak in a file added to the
# workspace later still fails the build. (It used to name four files explicitly,
# which made the policy.py exemption below dead code and left anything new
# unchecked.) File PRESENCE is checked unconditionally -- no exemption there.
if docker run --rm --entrypoint bash "$AGENT_IMG" -c '
      ls /opt/nanoslm_arch/data/val.bin 2>/dev/null;
      ls /opt/nanoslm_arch 2>/dev/null;
      find /app -type f | while read -r f; do
        [ "$f" = /app/policy.py ] && continue;
        grep -il "val\.bin\|/opt/nanoslm_arch" "$f" 2>/dev/null;
      done
   ' | grep -q .; then
  echo "FATAL: held-out data or its identity is reachable from the AGENT image"
  exit 1
fi

echo "[check] judge must NOT carry a GPU stack (it dispatches to Modal)"
if docker run --rm --entrypoint bash "$JUDGE_IMG" -c \
     'python3 -c "import torch" 2>/dev/null && echo present'  | grep -q present; then
  echo "FATAL: torch present in the CPU-only judge image -- a silent LOCAL"
  echo "       fallback would try to train ~190M at ctx 8192 on CPU"
  exit 1
fi

echo "[check] judge must hold both token streams AND the byte-count manifest"
docker run --rm --entrypoint bash "$JUDGE_IMG" -c \
  'test -s /opt/nanoslm_arch/data/train.bin \
   && test -s /opt/nanoslm_arch/data/val.bin \
   && test -s /opt/nanoslm_arch/data/manifest.json' \
  || { echo "FATAL: judge image missing a token stream or manifest.json"; exit 1; }

cat <<EOF

built:
  $AGENT_IMG
  $JUDGE_IMG

REMINDER: the GPU image is NOT built here. Deploy it separately and keep its
pins (torch 2.6.0 / triton 3.2.0 / flash-linear-attention 0.5.1) in sync:

  modal deploy harness/modal_app.py
EOF

#!/usr/bin/env bash
# Validate every generated prove-or-disprove problem: its compiled statement
# must be exactly `True ↔ Q` (see ShapeCheck.lean). Requires docker and the
# prebuilt eval image. Run after (re)generation, especially on submodule bumps.
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FC_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

FIRST_CFG=$(find "$FC_ROOT" -mindepth 3 -maxdepth 3 -name config.yaml -print -quit)
if [ -z "$FIRST_CFG" ]; then
  echo "no generated problems found (run generate.py first)" >&2
  exit 1
fi
IMAGE=$(awk '/image:/ {print $2; exit}' "$FIRST_CFG")

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
python3 - "$FC_ROOT" > "$TMP/targets.txt" <<'EOF'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
for tj in sorted(root.glob("*/*/target.json")):
    t = json.loads(tj.read_text(encoding="utf-8"))
    if t.get("mode") == "prove_or_disprove":
        print(" ".join(t["module"]) + " / " + " ".join(t["theorem"]))
EOF
echo "checking $(wc -l < "$TMP/targets.txt") prove-or-disprove targets against $IMAGE"
cp "$SCRIPT_DIR/ShapeCheck.lean" "$TMP/"
chmod -R a+rX "$TMP"
docker run --rm -v "$TMP":/sc:ro "$IMAGE" \
  bash -c 'cd /opt/formal-conjectures && lake env lean --root /sc --run /sc/ShapeCheck.lean /sc/targets.txt'

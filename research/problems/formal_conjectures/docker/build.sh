#!/usr/bin/env bash
# Build (and optionally push) the formal_conjectures evaluation image.
#
# The image tag is derived from the third_party/formal-conjectures submodule
# pin so the image and the generated problems can never drift apart silently.
#
# Usage: ./build.sh [--push]
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../../.." && pwd)
SUBMODULE="$REPO_ROOT/third_party/formal-conjectures"

if [ ! -f "$SUBMODULE/lean-toolchain" ]; then
    echo "ERROR: submodule not initialized. Run: git submodule update --init" >&2
    exit 1
fi

FC_REF=$(git -C "$SUBMODULE" describe --tags --exact-match)
IMAGE="${IMAGE:-shangyint/formal-conjectures-eval}"

echo "Building $IMAGE:$FC_REF (formal-conjectures @ $FC_REF)"
docker build --build-arg "FC_REF=$FC_REF" -t "$IMAGE:$FC_REF" "$SCRIPT_DIR"

if [ "${1:-}" = "--push" ]; then
    docker push "$IMAGE:$FC_REF"
fi

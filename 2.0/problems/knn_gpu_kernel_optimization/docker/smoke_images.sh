#!/usr/bin/env bash
# Smoke test for the built (intentionally torch-less) images: confirm the host-side
# harness imports (modal + flash_gpu) and that the frozen baseline + package parse.
# torch/triton live on the Modal image, so the packages are py_compiled here (a
# torch-less parse check), not imported. No GPU / Modal tokens required.
set -euo pipefail

AGENT_TAG=${AGENT_TAG:-frontiercs/knn-gpu-kernel-optimization-agent:experimental-v0.2.0}
JUDGE_TAG=${JUDGE_TAG:-frontiercs/knn-gpu-kernel-optimization-judge:experimental-v0.2.0}

SMOKE='import sys, modal, py_compile, pathlib
sys.path.insert(0, "/opt"); import flash_gpu
for root in sys.argv[1:]:
    for p in pathlib.Path(root).rglob("*.py"):
        py_compile.compile(str(p), doraise=True)
print("ok: modal + flash_gpu import; knn baseline + knnlib parse")'

echo "== agent image =="
docker run --rm -w /app "$AGENT_TAG" python3 -c "$SMOKE" /opt/knn_ref /app/knnlib

echo "== judge image =="
docker run --rm "$JUDGE_TAG" python3 -c "$SMOKE" /opt/knn_ref /opt/knnlib-clean/knnlib

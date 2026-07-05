"""Public GPU self-test for the K-Means kernel-optimization task.

Times your current /app/kmeanslib against the naive baseline on a Modal GPU and
reports the quality value + speedup on two public shapes. Requires
MODAL_TOKEN_ID / MODAL_TOKEN_SECRET in the environment. The graded workloads and
their thresholds are hidden and differ from these public shapes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, "/opt")

APP_DIR = os.environ.get("APP_DIR", "/app")
PKG = "kmeanslib"
BASELINE_DIR = "/opt/kmeans_ref"

PUBLIC_WORKLOADS = [
    {"id": "p0", "N": 50_000, "D": 32, "K": 64, "max_iters": 1, "seed": 1},
    {"id": "p1", "N": 200_000, "D": 128, "K": 256, "max_iters": 1, "seed": 2},
]

CFG = {
    "primitive": "kmeans",
    "pkg": PKG,
    "ref_module": "refkmeans",
    "gpu": os.environ.get("FLASH_PUBLIC_GPU", "H100"),
    "cuda_image": "nvidia/cuda:12.4.1-devel-ubuntu22.04",
    "pip": ["torch", "numpy"],
    "app_name": "kmeans-kernel-opt-public",
    "modal_timeout_seconds": 1800,
    "warmup": 2,
    "iters": 5,
    "aggregate": "mean",
    "inertia_tolerance": 0.02,
    "recall_threshold": 0.99,
    "captured_tolerance": 0.02,
    "ortho_tolerance": 0.02,
}


def _read(root: str, sub: str = "") -> dict:
    base = Path(root)
    scan = base / sub if sub else base
    return {str(p.relative_to(base)): p.read_text(encoding="utf-8", errors="replace")
            for p in scan.rglob("*.py")}


def main() -> int:
    import flash_gpu  # baked at /opt/flash_gpu.py
    if not flash_gpu.modal_available():
        print("Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET to run the GPU public test.")
        return 1
    payload = {
        "baseline_files": _read(BASELINE_DIR),
        "patched_files": _read(APP_DIR, PKG),
        "workloads": PUBLIC_WORKLOADS,
        "cfg": CFG,
    }
    try:
        result = flash_gpu.run_remote(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"GPU run failed: {exc}")
        return 1
    if not result.get("ok"):
        print(f"worker error: {result.get('error')}")
        return 1
    # Correctness first: show the quality metric (agent vs frozen baseline) on every
    # shape, pass or fail -- not just the speedup. The graded shapes are hidden and differ.
    prim = CFG.get("primitive", "")
    if prim in ("knn", "ivfpq"):
        mlabel, gate = "recall@k", f">= {CFG.get('recall_threshold')}"
    elif prim == "dbscan":
        mlabel, gate = "ARI", f">= {CFG.get('ari_threshold')}"
    elif prim == "kmeans":
        mlabel, gate = "inertia", f"<= (1+{CFG.get('inertia_tolerance')}) x ref (lower is better)"
    else:
        mlabel, gate = "quality", ""
    print(f"correctness gate: {mlabel} {gate}")
    print(f"{'workload':9s} {'status':22s} {'speedup':>9s}   {mlabel}: agent / ref")
    for row in result["rows"]:
        av, rv = row.get("agent_val"), row.get("ref_val")
        q = (f"{av:.4f} / {rv:.4f}"
             if isinstance(av, (int, float)) and isinstance(rv, (int, float)) else "n/a")
        sp = f"{row['speedup']:.2f}x" if row.get("ok") else "-"
        st = "OK" if row.get("ok") else "FAIL:" + str(row.get("reason", ""))
        print(f"{row['id']:9s} {st:22s} {sp:>9s}   {q}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

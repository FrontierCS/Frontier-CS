"""Public GPU self-test for the DBSCAN kernel-optimization task.

Times your current /app/dbscanlib against the naive baseline on a Modal GPU and
reports the clustering-agreement (ARI) verdict + speedup on two public shapes.
Requires MODAL_TOKEN_ID / MODAL_TOKEN_SECRET. The graded workloads and thresholds
are hidden and differ from these public shapes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, "/opt")

APP_DIR = os.environ.get("APP_DIR", "/app")
PKG = "dbscanlib"
BASELINE_DIR = "/opt/dbscan_ref"

PUBLIC_WORKLOADS = [
    {"id": "p0", "N": 100000, "D": 2, "n_centers": 12, "eps": 1.5, "min_samples": 8, "noise_frac": 0.03, "seed": 1},
    {"id": "p1", "N": 150000, "D": 2, "n_centers": 14, "eps": 1.4, "min_samples": 8, "noise_frac": 0.04, "seed": 2},
]

CFG = {
    "primitive": "dbscan",
    "pkg": PKG,
    "ref_module": "refdbscan",
    "gpu": os.environ.get("FLASH_PUBLIC_GPU", "H100"),
    "cuda_image": "nvidia/cuda:12.4.1-devel-ubuntu22.04",
    "pip": ["torch", "numpy"],
    "app_name": "dbscan-kernel-opt-public",
    "modal_timeout_seconds": 1800,
    "warmup": 2,
    "iters": 5,
    "inertia_tolerance": 0.02,
    "recall_threshold": 0.99,
    "captured_tolerance": 0.02,
    "ortho_tolerance": 0.02,
    "ari_threshold": 0.99,
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
    print(f"{'workload':10s} {'status':16s} {'speedup':>10s}")
    for row in result["rows"]:
        if row.get("ok"):
            print(f"{row['id']:10s} {'OK':16s} {row['speedup']:>9.2f}x")
        else:
            print(f"{row['id']:10s} {'FAIL:' + str(row.get('reason', '')):16s} {'-':>10s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Public GPU self-test for the IVF-PQ search kernel-optimization task.

Times your current /app/ivfpqlib against the naive baseline on a Modal GPU and
reports the iso-result recall verdict + speedup on two public shapes. The index
is built once per shape by the frozen baseline and reused. Requires
MODAL_TOKEN_ID / MODAL_TOKEN_SECRET. The graded workloads and thresholds are
hidden and differ from these public shapes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, "/opt")

APP_DIR = os.environ.get("APP_DIR", "/app")
PKG = "ivfpqlib"
BASELINE_DIR = "/opt/ivfpq_ref"

PUBLIC_WORKLOADS = [
    {"id": "p0", "M": 40000, "D": 64, "nlist": 256, "m": 8, "nprobe": 8, "Q": 1024, "k": 10, "seed": 1},
    {"id": "p1", "M": 100000, "D": 96, "nlist": 512, "m": 12, "nprobe": 16, "Q": 1024, "k": 10, "seed": 2},
]

CFG = {
    "primitive": "ivfpq",
    "pkg": PKG,
    "ref_module": "refivfpq",
    "gpu": os.environ.get("FLASH_PUBLIC_GPU", "H100"),
    "cuda_image": "nvidia/cuda:12.4.1-devel-ubuntu22.04",
    "pip": ["torch", "numpy"],
    "app_name": "ivfpq-kernel-opt-public",
    "modal_timeout_seconds": 1800,
    "warmup": 2,
    "iters": 5,
    "recall_threshold": 0.95,
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

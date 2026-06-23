#!/usr/bin/env python3
"""Measure the reference (exact, brute-force) baseline throughput -> baseline.json.

Operator tooling — NOT agent-facing. Runs at judge-image build time. Mirrors the
evaluator's reference: an exact Faiss IndexFlatL2 over the base vectors, queried
with the same Q query set and CONCURRENCY, timed to produce baseline_qps. The
candidate must beat this baseline_qps to score.

NOTE (resource + fairness): an exact FlatL2 over N=100M holds the vectors as
float32 in RAM (~51 GB), so this step needs a large-RAM BUILD host. The resulting
baseline reflects the build host, not the 8 GiB eval container — bake it
deliberately. Parametrized by N/Q so it is testable at small scale.

    N=2000 Q=256 python3 build_baseline.py <data_root>
"""

from __future__ import annotations

import json
import os
import struct
import sys
import time
from pathlib import Path

import numpy as np

DIM = 128
N = int(os.environ.get("FRONTIER_VECTOR_DB_N", "100000000"))
Q = int(os.environ.get("FRONTIER_VECTOR_DB_Q", "10000"))
TOP_K = int(os.environ.get("FRONTIER_VECTOR_DB_TOP_K", "10"))
CONCURRENCY = int(os.environ.get("FRONTIER_VECTOR_DB_CONCURRENCY", "8"))
ADD_BATCH = int(os.environ.get("FRONTIER_VECTOR_DB_REFERENCE_BATCH_SIZE", "50000"))


def _load_u8_matrix(path: Path, rows: int) -> np.memmap:
    with path.open("rb") as f:
        npts, dim = struct.unpack("<II", f.read(8))
    if dim != DIM:
        raise RuntimeError(f"{path}: dim {dim} != {DIM}")
    return np.memmap(path, dtype=np.uint8, mode="r", offset=8, shape=(rows, DIM))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: build_baseline.py <data_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    base = _load_u8_matrix(root / "index_100M" / "100M.u8bin", N)
    queries = _load_u8_matrix(root / "index_100M" / "query.bin", Q)

    import faiss  # noqa: PLC0415 — only needed here, present in the judge image

    faiss.omp_set_num_threads(CONCURRENCY)
    index = faiss.IndexFlatL2(DIM)
    print(f"[baseline] adding {N:,} vectors to FlatL2 (float32, ~{N * DIM * 4 / 1e9:.0f} GB RAM) ...")
    for start in range(0, N, ADD_BATCH):
        end = min(start + ADD_BATCH, N)
        index.add(np.asarray(base[start:end], dtype=np.float32))

    qf = np.asarray(queries[:Q], dtype=np.float32)
    # Warm up, then time the exact search of the full query set.
    index.search(qf[: min(32, Q)], TOP_K)
    t0 = time.perf_counter()
    index.search(qf, TOP_K)
    baseline_seconds = max(time.perf_counter() - t0, 1e-9)
    baseline_qps = Q / baseline_seconds

    out = root / "private_100M" / "baseline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "baseline_seconds": baseline_seconds,
                "baseline_qps": baseline_qps,
                "baseline_load_seconds": 0.0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[baseline] {Q:,} queries in {baseline_seconds:.3f}s -> baseline_qps={baseline_qps:.3f}")
    print(f"[baseline] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

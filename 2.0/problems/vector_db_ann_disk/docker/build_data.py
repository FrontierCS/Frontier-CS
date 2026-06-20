#!/usr/bin/env python3
"""Download + slice the real BIGANN SIFT100M benchmark data for vector_db_ann_disk.

Operator tooling — NOT agent-facing. Runs at judge-image build time. Produces the
vectors / query / ground-truth files from the public big-ann-benchmarks BIGANN
dataset (https://big-ann-benchmarks.com), with zero manual download or hosting:

    index_100M/100M.u8bin   first N rows of base.1B.u8bin (header rewritten to N)
    index_100M/query.bin    query.public.10K.u8bin (10,000 x 128 uint8)
    private_100M/truth.bin  top-TOP_K ids per query, sliced from the official GT

The DiskANN graph + PQ files are produced separately by build_index.sh; the
baseline by build_baseline.py.

Parametrized by N / Q / TOP_K so the pipeline is testable at small scale:
    N=1000 Q=10000 python3 build_data.py /tmp/data
"""

from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

import numpy as np

BIGANN = "https://dl.fbaipublicfiles.com/billion-scale-ann-benchmarks"
BASE_URL = f"{BIGANN}/bigann/base.1B.u8bin"
QUERY_URL = f"{BIGANN}/bigann/query.public.10K.u8bin"
GT_URL = f"{BIGANN}/GT_100M/bigann-100M"  # exact top-100 of the 100M subset

DIM = 128
N = int(os.environ.get("FRONTIER_VECTOR_DB_N", "100000000"))
Q = int(os.environ.get("FRONTIER_VECTOR_DB_Q", "10000"))
TOP_K = int(os.environ.get("FRONTIER_VECTOR_DB_TOP_K", "10"))


def _load_u8(path: Path, rows: int) -> np.memmap:
    import struct

    with path.open("rb") as f:
        _, dim = struct.unpack("<II", f.read(8))
    if dim != DIM:
        raise RuntimeError(f"{path}: dim {dim} != {DIM}")
    return np.memmap(path, dtype=np.uint8, mode="r", offset=8, shape=(rows, DIM))


def _get(url: str, byte_range: tuple[int, int] | None = None) -> bytes:
    req = urllib.request.Request(url)
    if byte_range is not None:
        req.add_header("Range", f"bytes={byte_range[0]}-{byte_range[1]}")
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def _stream_to(url: str, dest: Path, byte_range: tuple[int, int] | None = None) -> None:
    req = urllib.request.Request(url)
    if byte_range is not None:
        req.add_header("Range", f"bytes={byte_range[0]}-{byte_range[1]}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=3600) as resp, tmp.open("wb") as out:
        chunk = 1 << 24  # 16 MiB
        while True:
            buf = resp.read(chunk)
            if not buf:
                break
            out.write(buf)
    tmp.rename(dest)


def build_base(out_dir: Path) -> None:
    """Range-download the first N rows of base.1B.u8bin and rewrite the header."""
    dest = out_dir / "100M.u8bin"
    if dest.exists() and dest.stat().st_size == 8 + N * DIM:
        print(f"[base] exists, skip: {dest}")
        return
    last = 8 + N * DIM - 1  # inclusive byte offset of the N-row prefix (incl. header)
    print(f"[base] downloading first {N:,} rows ({(8 + N * DIM) / 1e9:.2f} GB) ...")
    _stream_to(BASE_URL, dest, byte_range=(0, last))
    # The source header says npts=1,000,000,000; rewrite to the N we kept.
    with dest.open("r+b") as f:
        f.seek(0)
        np.asarray([N, DIM], dtype=np.uint32).tofile(f)
    print(f"[base] wrote {dest} ({dest.stat().st_size:,} bytes)")


def build_query(out_dir: Path) -> None:
    dest = out_dir / "query.bin"
    if dest.exists() and dest.stat().st_size >= 8 + Q * DIM:
        print(f"[query] exists, skip: {dest}")
        return
    print("[query] downloading query.public.10K.u8bin ...")
    _stream_to(QUERY_URL, dest)
    head = np.fromfile(dest, dtype=np.uint32, count=2)
    print(f"[query] header npts={head[0]:,} dim={head[1]} (need >= {Q:,} x {DIM})")
    if head[1] != DIM or head[0] < Q:
        raise RuntimeError("query file header mismatch")


def _write_truth(dest: Path, top: np.ndarray) -> None:
    # Self-describing header [Q, TOP_K] then the ids (the evaluator strips it).
    with dest.open("wb") as f:
        np.asarray([Q, TOP_K], dtype=np.uint32).tofile(f)
        top.astype(np.uint32, copy=False).tofile(f)


def _truth_from_official_gt(dest: Path) -> None:
    """Slice the official exact GT (top-100 of the 100M subset) to top-TOP_K."""
    print("[truth] downloading official GT_100M ...")
    arr = np.frombuffer(_get(GT_URL), dtype=np.uint32)
    npts, k = int(arr[0]), int(arr[1])
    ids = arr[2 : 2 + npts * k].reshape(npts, k)
    if npts < Q or k < TOP_K:
        raise RuntimeError(f"GT too small: npts={npts} k={k}; need {Q} x {TOP_K}")
    top = ids[:Q, :TOP_K]
    if int(top.max()) >= N:
        raise RuntimeError(
            f"GT ids exceed N={N:,} (max {int(top.max()):,}); the official GT only "
            "matches the full 100M subset — use N=100000000 or compute_truth"
        )
    _write_truth(dest, top)
    print(f"[truth] wrote {dest} from official GT ({Q:,} x {TOP_K}; src k={k})")


def _truth_compute_exact(dest: Path, index_dir: Path) -> None:
    """Compute exact top-TOP_K from the local base via Faiss (small-scale builds).

    The official GT only matches the full 100M subset, so any other N must
    recompute truth against the actual base that was built."""
    import faiss  # noqa: PLC0415

    print(f"[truth] computing exact top-{TOP_K} over N={N:,} via Faiss FlatL2 ...")
    base = _load_u8(index_dir / "100M.u8bin", N)
    queries = _load_u8(index_dir / "query.bin", Q)
    index = faiss.IndexFlatL2(DIM)
    for s in range(0, N, 50000):
        index.add(np.asarray(base[s : min(s + 50000, N)], dtype=np.float32))
    _, ids = index.search(np.asarray(queries[:Q], dtype=np.float32), TOP_K)
    _write_truth(dest, ids)
    print(f"[truth] wrote {dest} (computed; {Q:,} x {TOP_K})")


def build_truth(out_dir: Path, index_dir: Path) -> None:
    dest = out_dir / "truth.bin"
    # The official BIGANN GT is exact only for the full 100M subset. For any
    # other N (smoke/small-scale builds) compute truth against the local base.
    compute = os.environ.get("FRONTIER_VECTOR_DB_COMPUTE_TRUTH", "").lower() in {"1", "true", "yes"}
    if N == 100_000_000 and not compute:
        _truth_from_official_gt(dest)
    else:
        _truth_compute_exact(dest, index_dir)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: build_data.py <data_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    index_dir = root / "index_100M"
    private_dir = root / "private_100M"
    index_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)

    build_query(index_dir)
    build_base(index_dir)
    build_truth(private_dir, index_dir)  # may compute from base (small-scale)
    print("[build_data] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

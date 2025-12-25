import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        self.nlist = int(kwargs.get("nlist", 8192))
        self.nprobe = int(kwargs.get("nprobe", 512))
        self.train_size = int(kwargs.get("train_size", 300_000))
        self.nthreads = int(kwargs.get("nthreads", max(1, min(8, os.cpu_count() or 1))))
        self.metric = "l2"

        self._index = None
        self._buffer = []
        self._buffer_rows = 0
        self._use_faiss = faiss is not None

        if self._use_faiss:
            try:
                faiss.omp_set_num_threads(self.nthreads)
            except Exception:
                pass

    def _ensure_index(self, n_total_hint: int) -> None:
        if not self._use_faiss:
            if self._index is None:
                self._index = {"xb": None}
            return

        if self._index is not None:
            return

        if n_total_hint <= 0:
            n_total_hint = 1

        # For small datasets, exact search is simplest and fast enough.
        if n_total_hint < max(10_000, self.nlist * 2):
            self._index = faiss.IndexFlatL2(self.dim)
            return

        nlist = min(self.nlist, max(1, n_total_hint // 60))
        nlist = max(1024, nlist)
        nlist = int(nlist)

        quantizer = faiss.IndexFlatL2(self.dim)
        self._index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, faiss.METRIC_L2)
        try:
            self._index.nprobe = int(self.nprobe)
        except Exception:
            pass

    def _maybe_train_from(self, xb: np.ndarray) -> None:
        if not self._use_faiss:
            return
        if self._index is None:
            return
        if not hasattr(self._index, "is_trained") or self._index.is_trained:
            return

        n = xb.shape[0]
        if n <= 0:
            return

        ts = min(self.train_size, n)
        if ts < min(10_000, n):
            ts = min(n, max(10_000, ts))
        ts = max(2_000, ts)

        if ts >= n:
            train_x = xb
        else:
            step = max(1, n // ts)
            train_x = xb[::step][:ts]
        train_x = np.ascontiguousarray(train_x, dtype=np.float32)

        self._index.train(train_x)

    def add(self, xb: np.ndarray) -> None:
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        n = xb.shape[0]
        if n == 0:
            return

        self._ensure_index(n_total_hint=n)

        if not self._use_faiss:
            if self._index["xb"] is None:
                self._index["xb"] = xb.copy()
            else:
                self._index["xb"] = np.vstack([self._index["xb"], xb])
            return

        if hasattr(self._index, "is_trained") and not self._index.is_trained:
            self._maybe_train_from(xb)

        self._index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        nq = xq.shape[0]
        if nq == 0:
            return (
                np.empty((0, k), dtype=np.float32),
                np.empty((0, k), dtype=np.int64),
            )

        if not self._use_faiss:
            xb = self._index["xb"]
            if xb is None or xb.shape[0] == 0:
                D = np.full((nq, k), np.float32(np.inf), dtype=np.float32)
                I = np.full((nq, k), -1, dtype=np.int64)
                return D, I

            xq_norm = (xq * xq).sum(axis=1, keepdims=True)
            xb_norm = (xb * xb).sum(axis=1, keepdims=True).T
            dots = xq @ xb.T
            dist = xq_norm + xb_norm - 2.0 * dots  # squared L2

            idx = np.argpartition(dist, kth=min(k - 1, dist.shape[1] - 1), axis=1)[:, :k]
            row = np.arange(nq)[:, None]
            dsel = dist[row, idx]
            order = np.argsort(dsel, axis=1)
            I = idx[row, order].astype(np.int64, copy=False)
            D = dsel[row, order].astype(np.float32, copy=False)
            return D, I

        if self._index is None:
            self._ensure_index(n_total_hint=1)

        if hasattr(self._index, "nprobe"):
            try:
                self._index.nprobe = int(self.nprobe)
            except Exception:
                pass

        D, I = self._index.search(xq, k)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        return D, I
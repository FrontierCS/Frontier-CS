import os
import numpy as np
from typing import Tuple

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


def _as_float32_c(x: np.ndarray) -> np.ndarray:
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    if not x.flags.c_contiguous:
        x = np.ascontiguousarray(x)
    return x


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", kwargs.get("efConstruction", 200)))
        self.ef_search = int(kwargs.get("ef_search", kwargs.get("efSearch", 1024)))
        self.n_threads = int(kwargs.get("n_threads", kwargs.get("num_threads", 0)) or 0)

        if self.n_threads <= 0:
            self.n_threads = int(os.environ.get("OMP_NUM_THREADS", "0") or 0)
        if self.n_threads <= 0:
            self.n_threads = min(8, os.cpu_count() or 1)

        self.index = None

        if faiss is not None:
            try:
                faiss.omp_set_num_threads(self.n_threads)
            except Exception:
                pass

            self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
            self.index.hnsw.efConstruction = self.ef_construction
            self.index.hnsw.efSearch = self.ef_search
            try:
                self.index.verbose = False
            except Exception:
                pass
        else:
            self._xb = None

    def add(self, xb: np.ndarray) -> None:
        xb = _as_float32_c(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        if self.index is not None:
            self.index.add(xb)
        else:
            if self._xb is None:
                self._xb = xb.copy()
            else:
                self._xb = np.vstack([self._xb, xb])

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        xq = _as_float32_c(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        if self.index is not None:
            ef = self.ef_search
            if k > 1:
                ef = max(ef, 32 * k)
            self.index.hnsw.efSearch = ef
            D, I = self.index.search(xq, k)
            return D, I

        if self._xb is None or self._xb.shape[0] == 0:
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        xb = self._xb
        nq = xq.shape[0]
        xb_norm = (xb * xb).sum(axis=1, keepdims=True).T
        xq_norm = (xq * xq).sum(axis=1, keepdims=True)
        D_all = xq_norm + xb_norm - 2.0 * (xq @ xb.T)
        idx = np.argpartition(D_all, kth=min(k - 1, D_all.shape[1] - 1), axis=1)[:, :k]
        row = np.arange(nq)[:, None]
        dsel = D_all[row, idx]
        order = np.argsort(dsel, axis=1)
        I = idx[row, order].astype(np.int64, copy=False)
        D = dsel[row, order].astype(np.float32, copy=False)
        return D, I
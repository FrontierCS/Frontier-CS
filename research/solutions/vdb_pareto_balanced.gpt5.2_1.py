import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 24))
        self.ef_construction = int(kwargs.get("ef_construction", 160))
        self.ef_search = int(kwargs.get("ef_search", 192))
        self.refine_k_factor = int(kwargs.get("refine_k_factor", 4))
        self.n_threads = int(kwargs.get("n_threads", min(8, os.cpu_count() or 1)))

        if faiss is None:
            raise RuntimeError("faiss is required in the evaluation environment")

        faiss.omp_set_num_threads(self.n_threads)

        base = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        base.hnsw.efConstruction = self.ef_construction
        base.hnsw.efSearch = self.ef_search

        if self.refine_k_factor and self.refine_k_factor > 1:
            idx = faiss.IndexRefineFlat(base)
            idx.k_factor = self.refine_k_factor
            self.index = idx
            self._base = base
        else:
            self.index = base
            self._base = base

        self._ntotal = 0

    @staticmethod
    def _as_float32_c(x: np.ndarray) -> np.ndarray:
        if x.dtype == np.float32 and x.flags.c_contiguous:
            return x
        return np.ascontiguousarray(x, dtype=np.float32)

    def add(self, xb: np.ndarray) -> None:
        xb = self._as_float32_c(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")
        self.index.add(xb)
        self._ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = self._as_float32_c(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        self._base.hnsw.efSearch = self.ef_search
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
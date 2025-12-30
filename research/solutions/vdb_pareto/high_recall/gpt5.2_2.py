import os
from typing import Tuple, Optional

import numpy as np

try:
    import faiss  # type: ignore
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        if faiss is None:
            raise ImportError("faiss is required but could not be imported") from None

        self.dim = int(dim)

        self.num_threads = int(kwargs.get("num_threads", min(8, os.cpu_count() or 1)))
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        self.metric = kwargs.get("metric", "l2")
        if self.metric in ("l2", "L2", faiss.METRIC_L2):
            self.faiss_metric = faiss.METRIC_L2
        elif self.metric in ("ip", "IP", "inner_product", faiss.METRIC_INNER_PRODUCT):
            self.faiss_metric = faiss.METRIC_INNER_PRODUCT
        else:
            self.faiss_metric = faiss.METRIC_L2

        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 800))

        self.index = faiss.IndexHNSWFlat(self.dim, self.M, self.faiss_metric)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

        self._ntotal = 0

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if not xb.flags["C_CONTIGUOUS"]:
            xb = np.ascontiguousarray(xb)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        self.index.add(xb)
        self._ntotal = int(self.index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if not xq.flags["C_CONTIGUOUS"]:
            xq = np.ascontiguousarray(xq)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        self.index.hnsw.efSearch = max(self.ef_search, k)

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
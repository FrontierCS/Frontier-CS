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
            raise RuntimeError("faiss is required but could not be imported")

        self.dim = int(dim)

        self.M = int(kwargs.get("M", 16))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 128))
        self.bounded_queue = bool(kwargs.get("bounded_queue", True))

        threads = kwargs.get("num_threads", None)
        if threads is None:
            threads = os.cpu_count() or 1
        self.num_threads = int(threads)
        if self.num_threads < 1:
            self.num_threads = 1

        faiss.omp_set_num_threads(self.num_threads)

        metric = kwargs.get("metric", "l2")
        if metric not in ("l2", "L2", faiss.METRIC_L2):
            raise ValueError("Only L2 metric is supported in this implementation")

        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search
        try:
            self.index.hnsw.search_bounded_queue = self.bounded_queue
        except Exception:
            pass

        self._warmed = False

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim})")

        faiss.omp_set_num_threads(self.num_threads)
        self.index.add(xb)

        if not self._warmed and self.index.ntotal > 0:
            q = np.zeros((1, self.dim), dtype=np.float32)
            try:
                _ = self.index.search(q, 1)
            except Exception:
                pass
            self._warmed = True

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim})")

        faiss.omp_set_num_threads(self.num_threads)

        ef = self.ef_search
        if k > 1:
            ef = max(ef, 64 * k)
        self.index.hnsw.efSearch = ef

        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
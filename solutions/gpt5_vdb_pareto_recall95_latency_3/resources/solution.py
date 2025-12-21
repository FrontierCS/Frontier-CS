import os
from typing import Tuple
import numpy as np

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 48))
        self.ef_construction = int(kwargs.get("ef_construction", 150))
        self.ef_search = int(kwargs.get("ef_search", 200))
        self.threads = int(kwargs.get("threads", max(1, (os.cpu_count() or 8))))
        self.metric = kwargs.get("metric", "L2")
        self._xb_count = 0

        if faiss is None:
            raise RuntimeError("faiss library is required but not available.")

        faiss.omp_set_num_threads(self.threads)

        if self.metric.upper() == "L2":
            self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        else:
            # Default to L2 if unknown
            self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)

        # Configure HNSW parameters
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"Input xb must have shape (N, {self.dim})")
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        faiss.omp_set_num_threads(self.threads)
        self.index.add(xb)
        self._xb_count += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self._xb_count == 0:
            raise RuntimeError("Index is empty. Call add() before search().")

        if not isinstance(xq, np.ndarray):
            xq = np.array(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"Input xq must have shape (nq, {self.dim})")
        xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Ensure efSearch set (can be adjusted by user between calls)
        self.index.hnsw.efSearch = int(self.ef_search)

        faiss.omp_set_num_threads(self.threads)
        D, I = self.index.search(xq, int(k))

        # Ensure dtypes and shapes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I

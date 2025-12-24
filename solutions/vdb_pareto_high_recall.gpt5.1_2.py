import os
from typing import Tuple

import numpy as np
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)

        # HNSW parameters with high recall defaults
        M = int(kwargs.get("M", 32))
        ef_construction = int(kwargs.get("ef_construction", 200))
        ef_search = int(kwargs.get("ef_search", 800))

        # Set FAISS to use available threads
        try:
            n_threads = os.cpu_count() or 1
            faiss.omp_set_num_threads(n_threads)
        except Exception:
            pass

        # Create HNSW-Flat index for L2 distance
        self.index = faiss.IndexHNSWFlat(self.dim, M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not isinstance(xq, np.ndarray):
            xq = np.array(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")
        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        nq = xq.shape[0]

        if self.index.ntotal == 0:
            distances = np.full((nq, k), np.inf, dtype=np.float32)
            indices = np.full((nq, k), -1, dtype=np.int64)
            return distances, indices

        D, I = self.index.search(xq, k)

        if not isinstance(D, np.ndarray):
            D = np.array(D, dtype=np.float32)
        if not isinstance(I, np.ndarray):
            I = np.array(I, dtype=np.int64)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I

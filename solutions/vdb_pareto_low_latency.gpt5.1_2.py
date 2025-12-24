import os
from typing import Tuple

import numpy as np
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW-based index optimized for low-latency approximate search.
        """
        self.dim = int(dim)
        if self.dim <= 0:
            raise ValueError("dim must be a positive integer")

        # HNSW parameters
        self.M = int(kwargs.get("M", 32))  # number of neighbors per node
        if self.M <= 0:
            self.M = 32

        self.ef_construction = int(kwargs.get("ef_construction", 200))
        if self.ef_construction <= 0:
            self.ef_construction = 200

        # Search time / recall tradeoff parameter
        # Higher ef_search -> higher recall, higher latency
        self.ef_search = int(kwargs.get("ef_search", 40))
        if self.ef_search <= 0:
            self.ef_search = 40

        # Threading
        num_threads = kwargs.get("num_threads", None)
        if num_threads is None:
            num_threads = os.cpu_count()
            if num_threads is None or num_threads <= 0:
                num_threads = 1
        self.num_threads = int(num_threads)
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except AttributeError:
            pass

        # Build HNSW-Flat index (L2 metric by default)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        hnsw = self.index.hnsw
        hnsw.efConstruction = self.ef_construction
        hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index.
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.
        """
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")
        if k <= 0:
            raise ValueError("k must be a positive integer")
        if self.index.ntotal == 0:
            raise RuntimeError("Index is empty. Call add() before search().")

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Ensure search parameter is set (in case user changed ef_search)
        self.index.hnsw.efSearch = self.ef_search

        D, I = self.index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I

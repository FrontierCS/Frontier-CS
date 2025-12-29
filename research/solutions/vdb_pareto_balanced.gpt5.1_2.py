import os
from typing import Tuple

import numpy as np
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize an HNSW index optimized for high recall under latency constraints.
        """
        self.dim = int(dim)

        # HNSW hyperparameters with sensible high-recall defaults
        self.M = int(kwargs.get("M", 16))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 256))

        # Threads for Faiss (use all available cores by default)
        n_threads = kwargs.get("n_threads", None)
        if n_threads is None:
            try:
                n_threads = os.cpu_count() or 1
            except Exception:
                n_threads = 1
        n_threads = int(max(1, n_threads))
        faiss.omp_set_num_threads(n_threads)

        # Create HNSW index (L2 metric by default)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. Can be called multiple times.
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors for each query vector.
        """
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        xq = np.ascontiguousarray(xq)

        # Ensure efSearch is set (allows user to modify between calls if desired)
        self.index.hnsw.efSearch = self.ef_search

        distances, indices = self.index.search(xq, int(k))

        # Ensure correct dtypes
        if distances.dtype != np.float32:
            distances = distances.astype(np.float32, copy=False)
        if indices.dtype != np.int64:
            indices = indices.astype(np.int64, copy=False)

        return distances, indices
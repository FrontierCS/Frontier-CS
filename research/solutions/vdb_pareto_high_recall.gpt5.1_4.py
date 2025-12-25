import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW-based index optimized for high recall under relaxed latency constraints.
        """
        self.dim = int(dim)

        # Hyperparameters with sensible high-recall defaults
        M = int(kwargs.get("M", 64))  # graph connectivity
        ef_construction = int(kwargs.get("ef_construction", 200))
        ef_search = int(kwargs.get("ef_search", 800))

        # Configure threading
        n_threads = kwargs.get("n_threads", None)
        if n_threads is None:
            if hasattr(faiss, "omp_get_max_threads"):
                n_threads = faiss.omp_get_max_threads()
        try:
            n_threads = int(n_threads) if n_threads is not None else None
        except (TypeError, ValueError):
            n_threads = None

        if n_threads is not None and n_threads > 0 and hasattr(faiss, "omp_set_num_threads"):
            faiss.omp_set_num_threads(n_threads)

        # Create HNSW index (L2 metric by default)
        self.index = faiss.IndexHNSWFlat(self.dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        self.ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"Expected xb shape (N, {self.dim}), got {xb.shape}")

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"Expected xq shape (nq, {self.dim}), got {xq.shape}")

        nq = xq.shape[0]

        if self.index.ntotal == 0:
            # Empty index: return infinities and -1 indices
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = -np.ones((nq, k), dtype=np.int64)
            return D, I

        if k > self.index.ntotal:
            k = self.index.ntotal

        # Ensure efSearch is set (in case user modified self.ef_search)
        self.index.hnsw.efSearch = int(self.ef_search)

        D, I = self.index.search(xq, k)

        # Normalize dtypes
        D = np.asarray(D, dtype=np.float32)
        I = np.asarray(I, dtype=np.int64)

        return D, I

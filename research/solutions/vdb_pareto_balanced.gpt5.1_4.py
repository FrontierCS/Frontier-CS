import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW-based index optimized for high recall under latency constraints.
        """
        self.dim = int(dim)

        # Hyperparameters with sensible defaults for SIFT1M
        M = int(kwargs.get("M", 32))
        ef_construction = int(kwargs.get("ef_construction", 200))
        ef_search = int(kwargs.get("ef_search", 128))
        num_threads = kwargs.get("num_threads", None)

        # Optional: limit / set FAISS threading
        if num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                pass

        # Initialize HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(self.dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index.
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)

        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"Expected xb shape (N, {self.dim}), got {xb.shape}")

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search k-NN for query vectors.
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)

        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"Expected xq shape (nq, {self.dim}), got {xq.shape}")

        distances, indices = self.index.search(xq, k)
        return distances, indices

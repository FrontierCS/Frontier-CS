import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the HNSW index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs:
                - M: HNSW graph degree (default: 32)
                - ef_construction: HNSW construction parameter (default: 200)
                - ef_search: HNSW search parameter (default: 256)
                - num_threads: number of FAISS threads (default: do not modify)
        """
        self.dim = dim

        # Hyperparameters with sensible defaults for high recall and good latency
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 256))

        # Optional control of FAISS threading
        num_threads = kwargs.get("num_threads", None)
        if num_threads is not None and hasattr(faiss, "omp_set_num_threads"):
            try:
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                pass  # fall back to FAISS default

        # Build HNSW index (L2 metric by default)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2 distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")
        if k <= 0:
            raise ValueError("k must be positive")

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Ensure efSearch is set (in case user modified it after initialization)
        self.index.hnsw.efSearch = self.ef_search

        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)
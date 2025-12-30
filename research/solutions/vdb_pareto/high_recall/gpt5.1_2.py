import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., M, ef_construction, ef_search)
        """
        self.dim = int(dim)

        # HNSW parameters tuned for high recall with relaxed latency budget
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 512))

        # Optional control over FAISS threading (otherwise use FAISS defaults)
        self.num_threads = kwargs.get("num_threads", None)
        if self.num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

        # Create HNSW index (L2 metric)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        try:
            self.index.metric_type = faiss.METRIC_L2
        except Exception:
            pass

        # Configure HNSW construction and search parameters
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

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
        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive")

        # Ensure search parameter is as configured
        self.index.hnsw.efSearch = self.ef_search

        distances, indices = self.index.search(xq, k)

        # Ensure correct dtypes
        if distances.dtype != np.float32:
            distances = distances.astype(np.float32, copy=False)
        if indices.dtype != np.int64:
            indices = indices.astype(np.int64, copy=False)

        return distances, indices
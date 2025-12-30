import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.

        Args:
            dim: Vector dimensionality (e.g., 128 for SIFT1M)
            **kwargs: Optional parameters (e.g., M, ef_construction, ef_search, num_threads)
        """
        self.dim = int(dim)

        # Hyperparameters with reasonable high-recall defaults
        self.M = int(kwargs.get("M", 32))
        self.efConstruction = int(
            kwargs.get("ef_construction", kwargs.get("efConstruction", 200))
        )
        self.efSearch = int(
            kwargs.get("ef_search", kwargs.get("efSearch", 256))
        )

        # Configure OpenMP threads
        max_threads = getattr(faiss, "omp_get_max_threads", lambda: 1)()
        default_threads = min(8, max_threads) if max_threads > 0 else 1
        self.num_threads = int(kwargs.get("num_threads", default_threads))
        if hasattr(faiss, "omp_set_num_threads"):
            faiss.omp_set_num_threads(self.num_threads)

        # Create HNSW index (L2 by default)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.efConstruction
        self.index.hnsw.efSearch = self.efSearch

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(
                f"xb must have shape (N, {self.dim}), got {xb.shape}"
            )

        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            (distances, indices):
                - distances: shape (nq, k), dtype float32, L2-squared distances
                - indices: shape (nq, k), dtype int64, indices into base vectors
        """
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(
                f"xq must have shape (nq, {self.dim}), got {xq.shape}"
            )

        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        # Ensure efSearch is set (in case user modified self.efSearch)
        self.index.hnsw.efSearch = self.efSearch

        D, I = self.index.search(xq, k)

        # Ensure expected dtypes and contiguity
        D = np.ascontiguousarray(D, dtype=np.float32)
        I = np.ascontiguousarray(I, dtype=np.int64)

        return D, I
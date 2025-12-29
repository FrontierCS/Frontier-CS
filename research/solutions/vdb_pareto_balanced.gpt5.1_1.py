import numpy as np
from typing import Tuple

import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Exact L2 index using Faiss IndexFlatL2.

        Args:
            dim: Vector dimensionality.
            **kwargs:
                num_threads (int, optional): number of OpenMP threads for Faiss.
        """
        self.dim = int(dim)

        # Configure Faiss threading
        num_threads = kwargs.get("num_threads", None)
        try:
            if num_threads is None:
                # Use maximum available threads
                num_threads = faiss.omp_get_max_threads()
            if isinstance(num_threads, int) and num_threads > 0:
                faiss.omp_set_num_threads(num_threads)
        except (AttributeError, RuntimeError):
            # If threading APIs are unavailable, silently ignore
            pass

        # Exact L2 index
        self.index = faiss.IndexFlatL2(self.dim)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb is None or xb.size == 0:
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
            distances: (nq, k) float32, L2-squared distances
            indices:   (nq, k) int64, indices into base vectors
        """
        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        nq = xq.shape[0]
        if k <= 0:
            return (
                np.empty((nq, 0), dtype=np.float32),
                np.empty((nq, 0), dtype=np.int64),
            )

        ntotal = self.index.ntotal
        if ntotal == 0:
            # No database vectors; return dummy results
            distances = np.full((nq, k), np.inf, dtype=np.float32)
            indices = np.full((nq, k), -1, dtype=np.int64)
            return distances, indices

        effective_k = min(k, ntotal)
        distances, indices = self.index.search(xq, effective_k)

        # If ntotal < k, pad with inf/-1 to maintain exact k neighbors
        if effective_k < k:
            padded_distances = np.full((nq, k), np.inf, dtype=np.float32)
            padded_indices = np.full((nq, k), -1, dtype=np.int64)
            padded_distances[:, :effective_k] = distances
            padded_indices[:, :effective_k] = indices
            distances, indices = padded_distances, padded_indices

        return distances, indices
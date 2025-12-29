import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        """
        self.dim = int(dim)

        # Hyperparameters with flexible naming
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(
            kwargs.get("ef_construction", kwargs.get("efConstruction", 200))
        )
        self.ef_search = int(
            kwargs.get("ef_search", kwargs.get("efSearch", 256))
        )

        # Build HNSW index (L2 metric, flat storage)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
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
        Search for k nearest neighbors of query vectors.
        """
        if k <= 0:
            raise ValueError("k must be positive")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim == 1:
            if xq.shape[0] != self.dim:
                raise ValueError(f"xq must have shape ({self.dim},) or (nq, {self.dim}), got {xq.shape}")
            xq = xq.reshape(1, -1)

        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Ensure efSearch is set (in case user modified after construction)
        self.index.hnsw.efSearch = self.ef_search

        distances, indices = self.index.search(xq, int(k))

        # Faiss already returns float32 distances and int64 indices
        return distances, indices
import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Uses a Faiss IndexFlatL2 (exact L2 search).
        """
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32, order="C")
        if xb.ndim == 1:
            xb = xb.reshape(1, -1)

        if xb.shape[1] != self.dim:
            raise ValueError(f"Expected vectors of dim {self.dim}, got {xb.shape[1]}")

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
        xq = np.asarray(xq, dtype=np.float32, order="C")
        if xq.ndim == 1:
            xq = xq.reshape(1, -1)

        if xq.shape[1] != self.dim:
            raise ValueError(f"Expected query vectors of dim {self.dim}, got {xq.shape[1]}")

        distances, indices = self.index.search(xq, k)
        return distances, indices

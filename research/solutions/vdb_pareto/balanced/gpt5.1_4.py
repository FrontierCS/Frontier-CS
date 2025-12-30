import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        """
        self.dim = int(dim)
        # Exact L2 index (brute-force with Faiss, but highly optimized)
        self.index = faiss.IndexFlatL2(self.dim)

        # Optional: allow overriding number of threads if provided
        n_threads = kwargs.get("n_threads", None)
        if n_threads is not None and hasattr(faiss, "set_num_threads"):
            try:
                faiss.set_num_threads(int(n_threads))
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.
        """
        if xb is None:
            return

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if xq is None:
            raise ValueError("xq cannot be None")
        if k <= 0:
            raise ValueError("k must be a positive integer")

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        nq = xq.shape[0]

        # If no vectors in the index, return empty results
        if self.index.ntotal == 0:
            distances = np.full((nq, k), np.inf, dtype=np.float32)
            indices = np.full((nq, k), -1, dtype=np.int64)
            return distances, indices

        # Effective k cannot exceed number of indexed vectors
        k_eff = min(k, self.index.ntotal)
        distances, indices = self.index.search(xq, k_eff)

        if k_eff < k:
            # Pad with inf distances and -1 indices if requested k > ntotal
            pad_d = np.full((nq, k - k_eff), np.inf, dtype=np.float32)
            pad_i = np.full((nq, k - k_eff), -1, dtype=np.int64)
            distances = np.concatenate((distances, pad_d), axis=1)
            indices = np.concatenate((indices, pad_i), axis=1)

        return distances, indices
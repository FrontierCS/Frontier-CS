import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the index for vectors of dimension `dim`.
        Uses an exact L2 (squared) Flat index from FAISS for maximum recall.
        """
        self.dim = dim

        # Ensure FAISS uses all available threads (typically matches number of vCPUs)
        try:
            max_threads = faiss.omp_get_max_threads()
            if isinstance(max_threads, int) and max_threads > 0:
                faiss.omp_set_num_threads(max_threads)
        except Exception:
            pass

        # Exact L2 index (squared Euclidean distance)
        self.index = faiss.IndexFlatL2(dim)

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index.
        """
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"Input xb must have shape (N, {self.dim})")

        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)

        xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"Input xq must have shape (nq, {self.dim})")

        if k <= 0:
            raise ValueError("k must be a positive integer")

        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)

        xq = np.ascontiguousarray(xq)

        D, I = self.index.search(xq, k)
        return D, I
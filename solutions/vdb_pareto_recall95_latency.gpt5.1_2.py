import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize an HNSW index for vectors of dimension `dim`.
        """
        self.dim = int(dim)

        # HNSW hyperparameters with reasonable defaults for high recall
        M = int(kwargs.get("M", 32))
        ef_construction = int(kwargs.get("ef_construction", 200))
        ef_search = int(kwargs.get("ef_search", 128))

        # Create HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(self.dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self._base_ef_search = ef_search
        self.index.hnsw.efSearch = ef_search

        # Use maximum available threads if OpenMP is enabled
        try:
            max_threads = faiss.omp_get_max_threads()
            if max_threads > 0:
                faiss.omp_set_num_threads(max_threads)
        except Exception:
            pass

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index.
        """
        if xb is None or xb.size == 0:
            return

        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"Input xb must have shape (N, {self.dim}), got {xb.shape}")

        if not xb.flags["C_CONTIGUOUS"] or xb.dtype != np.float32:
            xb = np.ascontiguousarray(xb, dtype=np.float32)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.
        """
        if k <= 0:
            raise ValueError("k must be positive")

        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"Input xq must have shape (nq, {self.dim}), got {xq.shape}")

        if not xq.flags["C_CONTIGUOUS"] or xq.dtype != np.float32:
            xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Adapt efSearch slightly based on k to preserve recall for larger k
        ef_search = max(self._base_ef_search, k * 8)
        if self.index.hnsw.efSearch != ef_search:
            self.index.hnsw.efSearch = ef_search

        D, I = self.index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32)
        if I.dtype != np.int64:
            I = I.astype(np.int64)

        return D, I

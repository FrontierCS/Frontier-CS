import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim

        # HNSW parameters with sensible defaults for high recall
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 256))

        # Set FAISS to use all available threads (if OpenMP is enabled)
        try:
            max_threads = faiss.omp_get_max_threads()
            if isinstance(max_threads, int) and max_threads > 0:
                faiss.omp_set_num_threads(max_threads)
        except Exception:
            pass

        # Initialize HNSW index (L2 metric by default)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        if xb.size == 0:
            return
        if xb.shape[1] != self.dim:
            raise ValueError(f"Input dimension {xb.shape[1]} does not match index dimension {self.dim}")
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.size == 0:
            return (
                np.empty((0, k), dtype=np.float32),
                np.empty((0, k), dtype=np.int64),
            )
        if xq.shape[1] != self.dim:
            raise ValueError(f"Query dimension {xq.shape[1]} does not match index dimension {self.dim}")
        xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Ensure efSearch is set (in case user changed it via kwargs)
        self.index.hnsw.efSearch = self.ef_search

        D, I = self.index.search(xq, k)

        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I

import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 200))
        self.num_threads = kwargs.get("num_threads", None)

        # Initialize HNSW index (no training needed)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        if self.num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)

        # set threads if specified
        if self.num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

        # set efSearch for HNSW
        self.index.hnsw.efSearch = int(self.ef_search)

        D, I = self.index.search(xq, int(k))
        return D, I
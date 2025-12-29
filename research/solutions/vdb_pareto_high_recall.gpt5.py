import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get('M', 32))
        self.ef_construction = int(kwargs.get('ef_construction', kwargs.get('efConstruction', 64)))
        self.ef_search = int(kwargs.get('ef_search', kwargs.get('efSearch', 800)))
        self.num_threads = kwargs.get('num_threads', None)

        if self.num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError("xb must be of shape (N, dim) and dtype float32")
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError("xq must be of shape (nq, dim) and dtype float32")
        # Ensure efSearch is sufficient for k
        ef_needed = max(self.ef_search, int(max(64, k * 64)))
        if self.index.hnsw.efSearch != ef_needed:
            self.index.hnsw.efSearch = ef_needed
        D, I = self.index.search(xq, int(k))
        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
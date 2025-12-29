import numpy as np
import faiss
import os
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim

        M = int(kwargs.get("M", 32))
        ef_construction = int(kwargs.get("ef_construction", 200))
        ef_search = int(kwargs.get("ef_search", 800))
        num_threads = kwargs.get("num_threads", None)

        # Configure FAISS threading
        try:
            if num_threads is not None:
                faiss.omp_set_num_threads(int(num_threads))
            else:
                ncpu = os.cpu_count() or 1
                faiss.omp_set_num_threads(int(ncpu))
        except Exception:
            pass

        # Build HNSW index
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search
        self._ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        if not xb.flags['C_CONTIGUOUS']:
            xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        if not xq.flags['C_CONTIGUOUS']:
            xq = np.ascontiguousarray(xq)

        # Ensure search parameter is set
        self.index.hnsw.efSearch = self._ef_search

        D, I = self.index.search(xq, k)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I
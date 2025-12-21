import numpy as np
from typing import Tuple
import os

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get('M', 32))
        self.ef_construction = int(kwargs.get('ef_construction', kwargs.get('efConstruction', 200)))
        self.ef_search = int(kwargs.get('ef_search', kwargs.get('efSearch', 256)))
        self.num_threads = kwargs.get('num_threads', None)
        self.index = None

        if faiss is not None:
            try:
                if self.num_threads is None:
                    nthreads = os.cpu_count() or 8
                    faiss.omp_set_num_threads(int(nthreads))
                else:
                    faiss.omp_set_num_threads(int(self.num_threads))
            except Exception:
                pass

    def add(self, xb: np.ndarray) -> None:
        if faiss is None:
            raise RuntimeError("faiss is required for this index")

        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)

        if self.index is None:
            idx = faiss.IndexHNSWFlat(self.dim, self.M)
            try:
                idx.hnsw.efConstruction = int(self.ef_construction)
            except Exception:
                pass
            try:
                idx.hnsw.efSearch = int(self.ef_search)
            except Exception:
                pass
            self.index = idx

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if faiss is None or self.index is None:
            raise RuntimeError("Index not initialized or faiss not available")

        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)

        try:
            self.index.hnsw.efSearch = int(self.ef_search)
        except Exception:
            pass

        D, I = self.index.search(xq, int(k))
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I

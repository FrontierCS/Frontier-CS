import numpy as np
import faiss
import multiprocessing
from typing import Tuple

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.M = int(kwargs.get("M", 48))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = kwargs.get("ef_search", None)
        self.num_threads = kwargs.get("num_threads", None)

        if self.num_threads is None:
            try:
                cpu_cnt = multiprocessing.cpu_count()
            except Exception:
                cpu_cnt = 8
            self.num_threads = min(8, max(1, cpu_cnt))

        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction

        if self.ef_search is None:
            try:
                max_threads = faiss.omp_get_max_threads()
            except Exception:
                max_threads = self.num_threads
            if max_threads >= 8:
                self.ef_search = 640
            elif max_threads >= 4:
                self.ef_search = 480
            else:
                self.ef_search = 320

        self.index.hnsw.efSearch = int(self.ef_search)

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not isinstance(xq, np.ndarray):
            xq = np.array(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass
        self.index.hnsw.efSearch = int(self.ef_search)
        D, I = self.index.search(xq, k)
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)
        return D, I
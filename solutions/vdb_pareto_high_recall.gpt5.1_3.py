import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 800))

        num_threads = kwargs.get("num_threads", None)
        try:
            if num_threads is None:
                num_threads = faiss.omp_get_max_threads()
            if isinstance(num_threads, str):
                num_threads = int(num_threads)
            if num_threads and num_threads > 0:
                faiss.omp_set_num_threads(num_threads)
        except Exception:
            pass

        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        try:
            self.index.metric_type = faiss.METRIC_L2
        except Exception:
            pass

        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

        self.ntotal = 0

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2:
            xb = xb.reshape(-1, self.dim)
        if xb.shape[1] != self.dim:
            raise ValueError("Input vectors have incorrect dimensionality.")

        if xb.shape[0] == 0:
            return

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)
        self.ntotal = int(self.index.ntotal)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        k = int(k)
        if k <= 0:
            raise ValueError("k must be positive.")

        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2:
            xq = xq.reshape(-1, self.dim)
        if xq.shape[1] != self.dim:
            raise ValueError("Query vectors have incorrect dimensionality.")

        nq = xq.shape[0]

        if self.ntotal == 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        try:
            target_ef = max(k, self.ef_search)
            if self.index.hnsw.efSearch < target_ef:
                self.index.hnsw.efSearch = target_ef
        except Exception:
            pass

        D, I = self.index.search(xq, k)

        if not isinstance(D, np.ndarray):
            D = np.array(D)
        if not isinstance(I, np.ndarray):
            I = np.array(I)

        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I

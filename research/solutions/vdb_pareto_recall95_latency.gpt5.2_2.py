import os
import numpy as np
from typing import Tuple

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 256))
        self.num_threads = int(kwargs.get("num_threads", max(1, min(8, os.cpu_count() or 1))))
        self.metric = kwargs.get("metric", "l2")

        if faiss is None:
            raise RuntimeError("FAISS is required but could not be imported.")

        faiss.omp_set_num_threads(self.num_threads)

        metric = None
        if isinstance(self.metric, str):
            m = self.metric.lower()
            if m in ("l2", "euclidean"):
                metric = faiss.METRIC_L2
            elif m in ("ip", "inner_product", "cosine"):
                metric = faiss.METRIC_INNER_PRODUCT
            else:
                metric = faiss.METRIC_L2
        else:
            metric = int(self.metric)

        if metric == faiss.METRIC_L2:
            self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        else:
            self.index = faiss.IndexHNSWFlat(self.dim, self.M, metric)

        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        if xb is None or xb.size == 0:
            return
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if k <= 0:
            raise ValueError("k must be >= 1")
        xq = np.ascontiguousarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        ntotal = int(self.index.ntotal)
        if ntotal == 0:
            nq = xq.shape[0]
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        kk = min(int(k), ntotal)
        D, I = self.index.search(xq, kk)

        if kk < k:
            nq = xq.shape[0]
            D2 = np.full((nq, k), np.inf, dtype=np.float32)
            I2 = np.full((nq, k), -1, dtype=np.int64)
            D2[:, :kk] = D
            I2[:, :kk] = I
            return D2, I2

        return D.astype(np.float32, copy=False), I.astype(np.int64, copy=False)
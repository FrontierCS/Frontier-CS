import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        High-recall HNSW index using FAISS.
        """
        self.dim = int(dim)

        # HNSW parameters tuned for high recall under relaxed latency
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 800))

        # Configure FAISS threading (use all available by default)
        num_threads = kwargs.get("num_threads", faiss.omp_get_max_threads())
        try:
            faiss.omp_set_num_threads(int(num_threads))
        except Exception:
            pass

        # Build HNSW index (no training needed)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

        self.ntotal = 0

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index.
        """
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)
        self.ntotal += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors for each query vector.
        """
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")

        nq = xq.shape[0]

        if self.ntotal == 0 or k <= 0:
            D = np.full((nq, k), np.inf, dtype=np.float32)
            I = np.full((nq, k), -1, dtype=np.int64)
            return D, I

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Ensure efSearch is at least max(default_ef_search, k)
        # (higher efSearch -> higher recall, more compute)
        ef_search = max(self.ef_search, k)
        self.index.hnsw.efSearch = ef_search

        # Cap k by ntotal for FAISS call, pad if necessary
        search_k = min(k, self.ntotal)
        D, I = self.index.search(xq, search_k)

        if search_k < k:
            D_pad = np.full((nq, k), np.inf, dtype=np.float32)
            I_pad = np.full((nq, k), -1, dtype=np.int64)
            D_pad[:, :search_k] = D
            I_pad[:, :search_k] = I
            D, I = D_pad, I_pad

        return D, I
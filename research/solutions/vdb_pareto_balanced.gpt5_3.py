import os
import numpy as np
from typing import Tuple

try:
    import faiss
except Exception:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 320))
        self.num_threads = int(kwargs.get("num_threads", max(1, (os.cpu_count() or 8))))
        self._index = None
        self._ntotal = 0

        if faiss is None:
            raise ImportError("FAISS-CPU is required for this solution.")
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        index = faiss.IndexHNSWFlat(self.dim, self.M)
        index.hnsw.efConstruction = self.ef_construction
        index.hnsw.efSearch = self.ef_search
        self._index = index

    def add(self, xb: np.ndarray) -> None:
        if xb is None or xb.size == 0:
            return
        if xb.shape[1] != self.dim:
            raise ValueError(f"Expected xb with dim={self.dim}, got {xb.shape[1]}")
        xb = np.ascontiguousarray(xb.astype(np.float32, copy=False))
        self._index.add(xb)
        self._ntotal = self._index.ntotal

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self._ntotal == 0:
            nq = xq.shape[0]
            return np.full((nq, k), np.inf, dtype=np.float32), np.full((nq, k), -1, dtype=np.int64)

        if xq.shape[1] != self.dim:
            raise ValueError(f"Expected xq with dim={self.dim}, got {xq.shape[1]}")

        xq = np.ascontiguousarray(xq.astype(np.float32, copy=False))
        try:
            faiss.omp_set_num_threads(self.num_threads)
        except Exception:
            pass

        # Ensure efSearch is set before querying
        try:
            self._index.hnsw.efSearch = max(self.ef_search, k)
        except Exception:
            pass

        k_eff = min(k, self._ntotal)
        D, I = self._index.search(xq, k_eff)

        if k_eff == k:
            return D, I

        # Pad results if requested k > ntotal
        nq = xq.shape[0]
        D_full = np.full((nq, k), np.inf, dtype=np.float32)
        I_full = np.full((nq, k), -1, dtype=np.int64)
        if k_eff > 0:
            D_full[:, :k_eff] = D
            I_full[:, :k_eff] = I
        return D_full, I_full
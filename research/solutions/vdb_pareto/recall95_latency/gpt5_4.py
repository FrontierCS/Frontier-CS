import numpy as np
from typing import Tuple, Optional
import os

try:
    import faiss
except Exception as e:
    faiss = None


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = int(dim)
        self.M = int(kwargs.get("M", 24))
        self.ef_construction = int(kwargs.get("ef_construction", 160))
        self.ef_search = int(kwargs.get("ef_search", 128))
        self.n_threads: Optional[int] = kwargs.get("n_threads", None)
        self._xb_added = 0

        if faiss is None:
            raise ImportError("faiss is required for this index implementation.")

        # Set FAISS threads (default to available CPUs)
        if self.n_threads is None:
            try:
                self.n_threads = max(1, int(os.environ.get("OMP_NUM_THREADS", os.cpu_count() or 1)))
            except Exception:
                self.n_threads = 1
        try:
            faiss.omp_set_num_threads(self.n_threads)
        except Exception:
            pass

        # Build HNSW index
        self.index = faiss.IndexHNSWFlat(self.dim, self.M, faiss.METRIC_L2)
        # Construction/search parameters
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        if not isinstance(xb, np.ndarray):
            xb = np.asarray(xb, dtype=np.float32)
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"xb must have shape (N, {self.dim}), got {xb.shape}")
        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)
        self._xb_added += xb.shape[0]

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if not isinstance(xq, np.ndarray):
            xq = np.asarray(xq, dtype=np.float32)
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"xq must have shape (nq, {self.dim}), got {xq.shape}")
        if self._xb_added == 0:
            raise RuntimeError("Search called before any vectors were added to the index.")
        k = int(k)
        if k <= 0:
            raise ValueError("k must be >= 1")

        # Ensure search parameters
        try:
            self.index.hnsw.efSearch = int(self.ef_search)
        except Exception:
            pass

        xq = np.ascontiguousarray(xq, dtype=np.float32)
        D, I = self.index.search(xq, k)

        # Ensure correct dtypes and contiguity
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I
import numpy as np
import faiss
from typing import Tuple
import os


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW index optimized for high recall on SIFT1M.
        """
        self.dim = int(dim)

        # Hyperparameters with sensible defaults for SIFT1M
        M = int(kwargs.get("M", 32))
        ef_construction = int(kwargs.get("ef_construction", kwargs.get("efConstruction", 200)))
        ef_search = int(kwargs.get("ef_search", kwargs.get("efSearch", 256)))
        self.ef_search = ef_search

        # Configure FAISS threading (cap at 8 threads by default)
        num_threads = kwargs.get("num_threads", None)
        if num_threads is None:
            try:
                max_threads_func = getattr(faiss, "omp_get_max_threads", None)
                if callable(max_threads_func):
                    max_threads = max_threads_func()
                else:
                    max_threads = os.cpu_count() or 1
                hw_threads = os.cpu_count() or 1
                num_threads = min(8, max_threads, hw_threads) if max_threads and hw_threads else 8
            except Exception:
                num_threads = 8
        try:
            faiss.omp_set_num_threads(int(num_threads))
        except Exception:
            pass

        # Create HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(self.dim, M)
        self.index.hnsw.efConstruction = ef_construction

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index.
        """
        if xb is None:
            return

        if not isinstance(xb, np.ndarray):
            xb = np.asarray(xb, dtype=np.float32)
        elif xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)

        if xb.ndim != 2 or xb.shape[1] != self.dim:
            xb = xb.reshape(-1, self.dim).astype(np.float32, copy=False)

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors using HNSW.
        """
        if not isinstance(xq, np.ndarray):
            xq = np.asarray(xq, dtype=np.float32)
        elif xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)

        if xq.ndim != 2 or xq.shape[1] != self.dim:
            xq = xq.reshape(-1, self.dim).astype(np.float32, copy=False)

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Set search parameter
        self.index.hnsw.efSearch = int(self.ef_search)

        D, I = self.index.search(xq, int(k))
        return D, I
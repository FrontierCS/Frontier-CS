import numpy as np
import faiss
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW-based index optimized for high recall under latency constraints.
        Parameters (with defaults chosen for SIFT1M):
            M: HNSW connectivity (default 32)
            ef_construction: construction exploration factor (default 200)
            ef_search: search exploration factor (default 800)
            num_threads: optional, number of FAISS threads
        """
        self.dim = dim

        M = int(kwargs.get("M", 32))
        ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 800))

        # Optional: control FAISS threading if requested
        num_threads = kwargs.get("num_threads", None)
        if num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                pass

        # Create HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        # efSearch will be set before each search call

    def add(self, xb: np.ndarray) -> None:
        if xb is None:
            return

        xb = np.asarray(xb, dtype=np.float32)
        if xb.ndim != 2 or xb.shape[1] != self.dim:
            xb = xb.reshape(-1, self.dim)

        xb = np.ascontiguousarray(xb, dtype=np.float32)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        xq = np.asarray(xq, dtype=np.float32)
        if xq.ndim != 2 or xq.shape[1] != self.dim:
            xq = xq.reshape(-1, self.dim)

        xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Ensure efSearch is set appropriately (can be adjusted per-call if desired)
        self.index.hnsw.efSearch = max(self.ef_search, k)

        D, I = self.index.search(xq, k)
        return D, I

import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        High-recall HNSW index based on Faiss.
        """
        self.dim = dim

        # HNSW parameters with high recall defaults
        self.M = int(kwargs.get("M", 32))
        self.ef_construction = int(kwargs.get("ef_construction", 200))
        self.ef_search = int(kwargs.get("ef_search", 1024))

        # Configure Faiss threading if specified
        num_threads = kwargs.get("num_threads", None)
        if num_threads is not None:
            try:
                faiss.omp_set_num_threads(int(num_threads))
            except Exception:
                pass

        # Create HNSW index with L2 metric
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the HNSW index.
        """
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32)
        if xb.dtype != np.float32 or not xb.flags["C_CONTIGUOUS"]:
            xb = np.ascontiguousarray(xb, dtype=np.float32)

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search k nearest neighbors for query vectors.
        """
        if not isinstance(xq, np.ndarray):
            xq = np.array(xq, dtype=np.float32)
        if xq.dtype != np.float32 or not xq.flags["C_CONTIGUOUS"]:
            xq = np.ascontiguousarray(xq, dtype=np.float32)

        # Ensure efSearch is set (allow user override via attribute if changed)
        self.index.hnsw.efSearch = int(getattr(self, "ef_search", self.index.hnsw.efSearch))

        D, I = self.index.search(xq, k)

        # Ensure correct dtypes
        if D.dtype != np.float32:
            D = D.astype(np.float32, copy=False)
        if I.dtype != np.int64:
            I = I.astype(np.int64, copy=False)

        return D, I

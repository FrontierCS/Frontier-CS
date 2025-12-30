import numpy as np
from typing import Tuple

import faiss
import multiprocessing


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW-based ANN index optimized for low latency and high recall.
        """
        self.dim = int(dim)

        # Hyperparameters with sensible defaults for SIFT1M / low-latency
        M = int(kwargs.get("M", 16))
        ef_construction = int(kwargs.get("ef_construction", 128))
        ef_search = int(kwargs.get("ef_search", 64))

        # Configure FAISS threading (parallel over queries)
        num_threads = kwargs.get("num_threads", None)
        if num_threads is None:
            try:
                num_threads = multiprocessing.cpu_count()
            except (ImportError, NotImplementedError):
                num_threads = 1
        try:
            if hasattr(faiss, "omp_set_num_threads"):
                faiss.omp_set_num_threads(int(num_threads))
        except Exception:
            pass

        # Build HNSW index (L2 metric by default)
        self.index = faiss.IndexHNSWFlat(self.dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index. Can be called multiple times.
        """
        if not isinstance(xb, np.ndarray):
            xb = np.array(xb, dtype=np.float32)
        else:
            if xb.dtype != np.float32:
                xb = xb.astype(np.float32)
            if not xb.flags["C_CONTIGUOUS"]:
                xb = np.ascontiguousarray(xb)

        if xb.ndim != 2 or xb.shape[1] != self.dim:
            raise ValueError(f"Input xb must have shape (N, {self.dim}), got {xb.shape}")

        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors for each query vector.
        """
        if not isinstance(xq, np.ndarray):
            xq = np.array(xq, dtype=np.float32)
        else:
            if xq.dtype != np.float32:
                xq = xq.astype(np.float32)
            if not xq.flags["C_CONTIGUOUS"]:
                xq = np.ascontiguousarray(xq)

        if xq.ndim != 2 or xq.shape[1] != self.dim:
            raise ValueError(f"Input xq must have shape (nq, {self.dim}), got {xq.shape}")

        D, I = self.index.search(xq, k)
        return D, I
import numpy as np
import faiss
import multiprocessing
from typing import Tuple


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        HNSW-based ANN index optimized for high recall with very low latency.
        """
        self.dim = dim

        # Hyperparameters with sensible defaults for SIFT1M on CPU
        M = int(kwargs.get("M", 32))  # number of neighbors in HNSW graph
        ef_construction = int(
            kwargs.get(
                "ef_construction",
                kwargs.get("efConstruction", 200),
            )
        )
        ef_search = int(
            kwargs.get(
                "ef_search",
                kwargs.get("efSearch", 128),
            )
        )

        # Set number of threads
        num_threads = kwargs.get("num_threads", None)
        if num_threads is None:
            try:
                num_threads = multiprocessing.cpu_count()
            except Exception:
                num_threads = 1
        if num_threads is None or num_threads <= 0:
            num_threads = 1
        faiss.omp_set_num_threads(int(num_threads))

        # Build HNSW index (L2 metric by default)
        self.index = faiss.IndexHNSWFlat(dim, M)
        # Configure HNSW parameters
        self.index.hnsw.efConstruction = ef_construction
        self.index.hnsw.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the index.
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search k nearest neighbors for query vectors.
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)
        xq = np.ascontiguousarray(xq)
        distances, indices = self.index.search(xq, k)
        return distances, indices
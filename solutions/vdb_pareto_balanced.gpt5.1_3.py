import numpy as np
from typing import Tuple
import faiss


class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        """
        Initialize the HNSW-based index for vectors of dimension `dim`.

        Optional kwargs:
            - M: HNSW graph degree (default: 32)
            - ef_construction: HNSW construction parameter (default: 200)
            - ef_search: HNSW search parameter (default: 1024)
            - num_threads: number of FAISS threads (default: faiss.omp_get_max_threads())
        """
        self.dim = dim

        M = int(kwargs.get("M", 32))
        ef_construction = int(kwargs.get("ef_construction", 200))
        ef_search = int(kwargs.get("ef_search", 1024))
        num_threads = kwargs.get("num_threads", None)

        # Configure FAISS threading
        try:
            if num_threads is not None and num_threads > 0:
                faiss.omp_set_num_threads(int(num_threads))
            else:
                # Use maximum available threads by default
                if hasattr(faiss, "omp_get_max_threads"):
                    faiss.omp_set_num_threads(faiss.omp_get_max_threads())
        except Exception:
            pass

        # Create HNSW index
        index = faiss.IndexHNSWFlat(dim, M)
        index.hnsw.efConstruction = ef_construction
        index.hnsw.efSearch = ef_search

        self.index = index

    def add(self, xb: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            xb: Base vectors, shape (N, dim), dtype float32
        """
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32, copy=False)
        xb = np.ascontiguousarray(xb)
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors of query vectors.

        Args:
            xq: Query vectors, shape (nq, dim), dtype float32
            k: Number of nearest neighbors to return

        Returns:
            distances: shape (nq, k), dtype float32, L2-squared distances
            indices: shape (nq, k), dtype int64, indices into base vectors
        """
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32, copy=False)
        xq = np.ascontiguousarray(xq)
        distances, indices = self.index.search(xq, k)
        return distances, indices

import os
from typing import Tuple

import numpy as np
import faiss


class YourIndexClass:
    def __init__(
        self,
        dim: int,
        M: int = 16,
        ef_construction: int = 200,
        ef_search: int = 100,
        num_threads: int = None,
        **kwargs,
    ):
        """
        HNSW index using Faiss, optimized for low-latency approximate NN search.
        """
        self.dim = dim
        self.M = int(M)
        self.ef_construction = int(ef_construction)
        self.ef_search = int(ef_search)

        # Configure number of threads for Faiss (global setting)
        if num_threads is None:
            num_threads = os.cpu_count() or 1
        faiss.omp_set_num_threads(int(num_threads))

        # Create HNSW index (L2 metric by default)
        self.index = faiss.IndexHNSWFlat(self.dim, self.M)
        self.index.hnsw.efConstruction = self.ef_construction
        self.index.hnsw.efSearch = self.ef_search

    def add(self, xb: np.ndarray) -> None:
        """
        Add base vectors to the HNSW index.
        """
        if xb is None or xb.size == 0:
            return
        xb = np.ascontiguousarray(xb, dtype="float32")
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search k nearest neighbors for query vectors.
        """
        if k <= 0:
            k = 1
        xq = np.ascontiguousarray(xq, dtype="float32")
        # Ensure efSearch is set (can be tuned per-call if desired)
        self.index.hnsw.efSearch = self.ef_search
        distances, indices = self.index.search(xq, k)
        return distances, indices
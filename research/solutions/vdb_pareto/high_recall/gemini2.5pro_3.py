import numpy as np
from typing import Tuple
import faiss

class YourIndexClass:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.m = kwargs.get("M", 64)
        self.ef_construction = kwargs.get("ef_construction", 500)
        self.ef_search = kwargs.get("ef_search", 1024)

        # HNSWFlat provides high recall without quantization errors.
        # METRIC_L2 corresponds to squared L2 distance, which is sufficient
        # and computationally cheaper than true L2.
        self.index = faiss.IndexHNSWFlat(self.dim, self.m, faiss.METRIC_L2)
        self.index.hnsw.efConstruction = self.ef_construction

    def add(self, xb: np.ndarray) -> None:
        # FAISS HNSW requires float32 data.
        if xb.dtype != np.float32:
            xb = xb.astype(np.float32)
        
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        if self.index.ntotal == 0:
            # Handle search on an empty index.
            nq = xq.shape[0]
            return (
                np.full((nq, k), np.inf, dtype=np.float32),
                np.full((nq, k), -1, dtype=np.int64),
            )

        # FAISS requires float32 data for queries as well.
        if xq.dtype != np.float32:
            xq = xq.astype(np.float32)

        # Set the search-time parameter `efSearch`. This is the most critical
        # parameter for the recall/latency trade-off in HNSW. A higher value
        # leads to a more exhaustive search, increasing recall at the cost of latency.
        # We set a very high default value to maximize recall given the relaxed latency constraint.
        self.index.hnsw.efSearch = self.ef_search

        distances, indices = self.index.search(xq, k)
        
        return distances, indices
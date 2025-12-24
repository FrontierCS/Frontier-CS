import numpy as np
import faiss
from typing import Tuple

class LatencyOptimizedIndex:
    def __init__(self, dim: int, **kwargs):
        M = kwargs.get("M", 16)
        ef_construction = kwargs.get("ef_construction", 200)
        ef_search = kwargs.get("ef_search", 32)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        distances, indices = self.index.search(xq, k)
        return distances, indices

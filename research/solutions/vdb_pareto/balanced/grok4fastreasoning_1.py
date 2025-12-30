import numpy as np
import faiss
from typing import Tuple

class BalancedIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        self.index = faiss.IndexHNSWFlat(dim, M=32)
        self.index.hnsw.efConstruction = 200
        self.ef_search = 300

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.ef = self.ef_search
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)
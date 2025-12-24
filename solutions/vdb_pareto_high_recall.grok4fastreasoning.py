import numpy as np
from typing import Tuple
import faiss

class HighRecallHNSWIndex:
    def __init__(self, dim: int, **kwargs):
        M = kwargs.get('M', 32)
        ef_construction = kwargs.get('ef_construction', 200)
        ef_search = kwargs.get('ef_search', 400)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.efConstruction = ef_construction
        self.ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.efSearch = self.ef_search
        distances, indices = self.index.search(xq, k)
        return distances.astype(np.float32), indices.astype(np.int64)

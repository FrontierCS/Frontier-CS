import numpy as np
import faiss
from typing import Tuple

class HighRecallIndex:
    def __init__(self, dim: int, **kwargs):
        self.dim = dim
        M = kwargs.get('M', 64)
        ef_construction = kwargs.get('ef_construction', 300)
        ef_search = kwargs.get('ef_search', 500)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.hnsw.efConstruction = ef_construction
        self.ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb)

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.hnsw.efSearch = self.ef_search
        distances, indices = self.index.search(xq, k)
        return distances, indices

import numpy as np
import faiss
from typing import Tuple

class HNSWIndex:
    def __init__(self, dim: int, **kwargs):
        M = kwargs.get('M', 64)
        ef_construction = kwargs.get('ef_construction', 200)
        ef_search = kwargs.get('ef_search', 200)
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.efConstruction = ef_construction
        self.index.efSearch = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype('float32'))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        distances, indices = self.index.search(xq.astype('float32'), k)
        return distances.astype('float32'), indices.astype('int64')

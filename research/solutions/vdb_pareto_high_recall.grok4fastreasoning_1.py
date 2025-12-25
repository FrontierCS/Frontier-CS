import numpy as np
from typing import Tuple
import faiss

class HighRecallHNSWIndex:
    def __init__(self, dim: int, **kwargs):
        M = kwargs.get('M', 64)
        ef_construction = kwargs.get('ef_construction', 500)
        ef_search = kwargs.get('ef_search', 1000)
        self.dim = dim
        self.index = faiss.IndexHNSWFlat(dim, M)
        self.index.efConstruction = ef_construction
        self.ef_search = ef_search

    def add(self, xb: np.ndarray) -> None:
        self.index.add(xb.astype('float32'))

    def search(self, xq: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        self.index.efSearch = self.ef_search
        D, I = self.index.search(xq.astype('float32'), k)
        return D, I
